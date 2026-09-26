"""Dashboard data querying and analytics service.

Connects directly to EcoTrace storage (SQLite or Memory) and computes
observability metrics using existing deterministic EcoTrace analysis modules.
"""

from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ecotrace.analysis.duplicates import DuplicateDetector
from ecotrace.analysis.efficiency import EfficiencyAnalyzer
from ecotrace.analysis.latency import LatencyAnalyzer
from ecotrace.analysis.tokens import TokenAnalyzer
from ecotrace.impact.carbon import CarbonEstimator
from ecotrace.impact.cost import CostCalculator
from ecotrace.impact.ecoscore import EcoScoreCalculator
from ecotrace.impact.energy import EnergyEstimator
from ecotrace.optimization.strategies import CachingStrategy
from ecotrace.storage.base import BaseStorage
from ecotrace.storage.models import RequestEvent
from ecotrace.storage.sqlite import SQLiteStorage


class DashboardService:
    """Service providing data models, aggregations, and metrics for the dashboard."""

    def __init__(self, storage: Optional[BaseStorage] = None, db_path: str = "ecotrace.db") -> None:
        self.db_path = db_path
        if storage is not None:
            self.storage = storage
        else:
            self.storage = SQLiteStorage(db_path=db_path)

        # Core EcoTrace analyzer instances
        self.token_analyzer = TokenAnalyzer()
        self.latency_analyzer = LatencyAnalyzer()
        self.duplicate_detector = DuplicateDetector()
        self.efficiency_analyzer = EfficiencyAnalyzer()
        self.cost_calculator = CostCalculator()
        self.energy_estimator = EnergyEstimator()
        self.carbon_estimator = CarbonEstimator()
        self.ecoscore_calculator = EcoScoreCalculator()
        self.caching_strategy = CachingStrategy()

    def _get_all_events(self) -> List[RequestEvent]:
        """Fetch all events from storage ordered by timestamp descending."""
        return self.storage.get_events(limit=100000, offset=0)

    def _filter_events_by_time(
        self,
        events: List[RequestEvent],
        time_range: str = "all",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[RequestEvent]:
        """Filter events by pre-defined or custom time range."""
        if not events:
            return []

        now = datetime.now(timezone.utc)
        if time_range == "24h":
            cutoff = now - timedelta(hours=24)
            return [e for e in events if e.timestamp and e.timestamp >= cutoff]
        elif time_range == "7d":
            cutoff = now - timedelta(days=7)
            return [e for e in events if e.timestamp and e.timestamp >= cutoff]
        elif time_range == "30d":
            cutoff = now - timedelta(days=30)
            return [e for e in events if e.timestamp and e.timestamp >= cutoff]
        elif time_range == "custom" and start_date and end_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                return [e for e in events if e.timestamp and start_dt <= e.timestamp <= end_dt]
            except Exception:
                return events
        return events

    def _calculate_event_cost(self, event: RequestEvent) -> Optional[float]:
        """Calculate estimated cost for a single event."""
        res = self.cost_calculator.estimate([event])
        return res.total_cost_usd

    @staticmethod
    def _round_cost(val: Optional[float], digits: int = 4) -> Optional[float]:
        """Safely round cost float or return None if cost is unavailable."""
        if val is None:
            return None
        return round(val, digits)

    @staticmethod
    def _sum_costs(costs: List[Optional[float]]) -> Optional[float]:
        """Sum costs list, returning None if pricing is unavailable for any item or list is empty without pricing."""
        if not costs:
            return None
        if any(c is None for c in costs):
            return None
        return sum(c for c in costs if c is not None)

    def _index_fingerprints(self, events: List[RequestEvent]) -> Dict[str, List[RequestEvent]]:
        """Group events by their deterministic request_hash, sorted chronologically."""
        groups: Dict[str, List[RequestEvent]] = defaultdict(list)
        for e in events:
            h = e.request_hash or "unhashed"
            groups[h].append(e)

        # Sort each group chronologically (oldest first)
        for h in groups:
            groups[h].sort(key=lambda x: x.timestamp or datetime.min.replace(tzinfo=timezone.utc))
        return groups

    def get_overview(self, time_range: str = "all") -> Dict[str, Any]:
        """Produce the comprehensive Overview KPIs and summary charts."""
        all_events = self._get_all_events()
        events = self._filter_events_by_time(all_events, time_range)

        total_requests = len(events)
        token_stats = self.token_analyzer.analyze(events)
        latency_stats = self.latency_analyzer.analyze(events)
        cost_est = self.cost_calculator.estimate(events)
        energy_est = self.energy_estimator.estimate(events)
        carbon_est = self.carbon_estimator.estimate(events)

        # Deterministic Duplicate Analysis
        fp_groups = self._index_fingerprints(events)
        duplicate_count = 0
        wasted_tokens = 0
        wasted_costs: List[Optional[float]] = []

        for h, group in fp_groups.items():
            if len(group) > 1:
                repeats = group[1:]  # Everything after the first occurrence
                duplicate_count += len(repeats)
                wasted_tokens += sum(e.total_tokens for e in repeats)
                for e in repeats:
                    wasted_costs.append(self._calculate_event_cost(e))

        wasted_cost = self._sum_costs(wasted_costs)
        duplicate_rate_pct = (duplicate_count / total_requests * 100) if total_requests > 0 else 0.0

        # EcoScore calculation
        ecoscore = self.ecoscore_calculator.calculate(
            events=events,
            duplicate_count=duplicate_count,
            wasted_tokens=wasted_tokens,
        )

        # Timeline aggregation (Requests over time & Tokens over time)
        # Group by hour if <= 2 days, else by day
        timeline_buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"requests": 0, "input_tokens": 0, "output_tokens": 0, "costs": [], "duplicates": 0}
        )

        # Determine interval format
        is_short_range = time_range in ("24h",)
        date_format = "%Y-%m-%d %H:00" if is_short_range else "%Y-%m-%d"

        # Chronological order for timeline
        chronological_events = sorted(
            events, key=lambda x: x.timestamp or datetime.min.replace(tzinfo=timezone.utc)
        )

        seen_hashes: set[str] = set()
        for e in chronological_events:
            ts = e.timestamp or datetime.now(timezone.utc)
            bucket_key = ts.strftime(date_format)
            bucket = timeline_buckets[bucket_key]
            bucket["requests"] += 1
            bucket["input_tokens"] += e.input_tokens
            bucket["output_tokens"] += e.output_tokens
            bucket["costs"].append(self._calculate_event_cost(e))
            if e.request_hash:
                if e.request_hash in seen_hashes:
                    bucket["duplicates"] += 1
                seen_hashes.add(e.request_hash)

        timeline_labels = sorted(timeline_buckets.keys())
        request_series = [timeline_buckets[k]["requests"] for k in timeline_labels]
        input_token_series = [timeline_buckets[k]["input_tokens"] for k in timeline_labels]
        output_token_series = [timeline_buckets[k]["output_tokens"] for k in timeline_labels]
        cost_series = [self._round_cost(self._sum_costs(timeline_buckets[k]["costs"]), 4) for k in timeline_labels]

        # Model usage summary table & chart
        model_groups: Dict[str, List[RequestEvent]] = defaultdict(list)
        for e in events:
            model_groups[e.model].append(e)

        models_summary: List[Dict[str, Any]] = []
        for model_name, m_events in sorted(model_groups.items(), key=lambda x: len(x[1]), reverse=True):
            m_cost = self.cost_calculator.estimate(m_events).total_cost_usd
            m_lat = self.latency_analyzer.analyze(m_events).avg_latency_ms
            m_tokens = sum(e.total_tokens for e in m_events)
            m_provider = m_events[0].provider if m_events else "unknown"

            # model duplicate count
            m_fps = self._index_fingerprints(m_events)
            m_dups = sum(len(g) - 1 for g in m_fps.values() if len(g) > 1)

            models_summary.append({
                "model": model_name,
                "provider": m_provider,
                "requests": len(m_events),
                "tokens": m_tokens,
                "input_tokens": sum(e.input_tokens for e in m_events),
                "output_tokens": sum(e.output_tokens for e in m_events),
                "cost": self._round_cost(m_cost, 4),
                "avg_latency": round(m_lat, 1),
                "duplicates": m_dups,
            })

        return {
            "kpis": {
                "total_requests": total_requests,
                "total_tokens": token_stats.total_tokens,
                "input_tokens": token_stats.total_input_tokens,
                "output_tokens": token_stats.total_output_tokens,
                "avg_latency_ms": round(latency_stats.avg_latency_ms, 1),
                "estimated_cost_usd": self._round_cost(cost_est.total_cost_usd, 4),
                "duplicate_requests": duplicate_count,
                "duplicate_rate_pct": round(duplicate_rate_pct, 1),
                "ecoscore": {
                    "score": ecoscore.score,
                    "grade": ecoscore.grade,
                    "components": ecoscore.components,
                },
                "energy": {
                    "total_wh": energy_est.total_wh,
                    "total_kwh": energy_est.total_kwh,
                },
                "carbon": {
                    "total_gco2": carbon_est.total_gco2,
                    "total_kgco2": carbon_est.total_kgco2,
                },
                "wasted_tokens": wasted_tokens,
                "wasted_cost_usd": self._round_cost(wasted_cost, 4),
            },
            "latency_distribution": {
                "avg": round(latency_stats.avg_latency_ms, 1),
                "p50": round(latency_stats.p50_latency_ms, 1),
                "p95": round(latency_stats.p95_latency_ms, 1),
                "p99": round(latency_stats.p99_latency_ms, 1),
                "min": round(latency_stats.min_latency_ms, 1),
                "max": round(latency_stats.max_latency_ms, 1),
            },
            "activity_chart": {
                "labels": timeline_labels,
                "requests": request_series,
            },
            "token_chart": {
                "labels": timeline_labels,
                "input_tokens": input_token_series,
                "output_tokens": output_token_series,
            },
            "cost_chart": {
                "labels": timeline_labels,
                "cost": cost_series,
            },
            "models_summary": models_summary,
            "total_stored_events": len(all_events),
        }

    def get_requests(
        self,
        search: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        duplicate_filter: Optional[str] = None,  # 'all', 'unique', 'repeated'
        time_range: str = "all",
        sort_by: str = "timestamp",  # 'timestamp', 'latency', 'cost', 'tokens'
        sort_order: str = "desc",   # 'asc', 'desc'
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Fetch and filter individual request records."""
        all_events = self._get_all_events()
        events = self._filter_events_by_time(all_events, time_range)

        # Compute occurrence counts across the entire dataset
        fp_groups = self._index_fingerprints(all_events)
        event_fp_info: Dict[str, Dict[str, Any]] = {}

        for h, group in fp_groups.items():
            for idx, e in enumerate(group):
                event_fp_info[e.request_id] = {
                    "is_duplicate": idx > 0,
                    "occurrence_number": idx + 1,
                    "total_occurrences": len(group),
                    "first_seen": group[0].timestamp.isoformat() if group[0].timestamp else None,
                    "last_seen": group[-1].timestamp.isoformat() if group[-1].timestamp else None,
                }

        # Apply search and filters
        filtered: List[RequestEvent] = []
        search_lower = search.strip().lower() if search else None

        for e in events:
            # Provider filter
            if provider and provider != "all" and e.provider.lower() != provider.lower():
                continue

            # Model filter
            if model and model != "all" and e.model.lower() != model.lower():
                continue

            # Duplicate filter
            fp_info = event_fp_info.get(e.request_id, {"is_duplicate": False})
            if duplicate_filter == "unique" and fp_info["is_duplicate"]:
                continue
            if duplicate_filter == "repeated" and not fp_info["is_duplicate"]:
                continue

            # Text search
            if search_lower:
                prompt_str = str(e.prompt).lower()
                response_str = str(e.response or "").lower()
                hash_str = str(e.request_hash or "").lower()
                req_id = str(e.request_id).lower()

                if not (
                    search_lower in prompt_str
                    or search_lower in response_str
                    or search_lower in hash_str
                    or search_lower in req_id
                    or search_lower in e.model.lower()
                    or search_lower in e.provider.lower()
                ):
                    continue

            filtered.append(e)

        # Sorting
        reverse = sort_order.lower() == "desc"
        if sort_by == "latency":
            filtered.sort(key=lambda x: x.latency_ms, reverse=reverse)
        elif sort_by == "cost":
            filtered.sort(
                key=lambda x: (self._calculate_event_cost(x) is None, self._calculate_event_cost(x) or 0.0),
                reverse=reverse,
            )
        elif sort_by == "tokens":
            filtered.sort(key=lambda x: x.total_tokens, reverse=reverse)
        else:  # timestamp
            filtered.sort(
                key=lambda x: x.timestamp or datetime.min.replace(tzinfo=timezone.utc),
                reverse=reverse,
            )

        total_filtered = len(filtered)
        paginated = filtered[offset : offset + limit]

        # Serialize rows with computed fields
        rows = []
        for e in paginated:
            fp_info = event_fp_info.get(e.request_id, {
                "is_duplicate": False,
                "occurrence_number": 1,
                "total_occurrences": 1,
            })
            cost = self._calculate_event_cost(e)
            rows.append({
                "request_id": e.request_id,
                "session_id": e.session_id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "provider": e.provider,
                "model": e.model,
                "request_hash": e.request_hash,
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "total_tokens": e.total_tokens,
                "latency_ms": round(e.latency_ms, 1),
                "estimated_cost_usd": self._round_cost(cost, 5),
                "is_duplicate": fp_info["is_duplicate"],
                "occurrence_number": fp_info["occurrence_number"],
                "total_occurrences": fp_info["total_occurrences"],
            })

        # Distinct providers & models for filter dropdowns
        distinct_providers = sorted(list({e.provider for e in all_events}))
        distinct_models = sorted(list({e.model for e in all_events}))

        return {
            "total": total_filtered,
            "limit": limit,
            "offset": offset,
            "requests": rows,
            "filter_options": {
                "providers": distinct_providers,
                "models": distinct_models,
            },
        }

    def get_request_details(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Fetch complete details for a single request."""
        event = self.storage.get_event(request_id)
        if event is None:
            return None

        all_events = self._get_all_events()
        fp_groups = self._index_fingerprints(all_events)
        group = fp_groups.get(event.request_hash or "", [])

        occurrence_idx = 1
        original_request_id = None
        for idx, item in enumerate(group):
            if item.request_id == event.request_id:
                occurrence_idx = idx + 1
            if idx == 0:
                original_request_id = item.request_id

        cost = self._calculate_event_cost(event)

        # Format prompt nicely
        prompt_display = event.prompt
        if isinstance(prompt_display, list):
            prompt_display_formatted = json.dumps(prompt_display, indent=2)
        elif isinstance(prompt_display, dict):
            prompt_display_formatted = json.dumps(prompt_display, indent=2)
        else:
            prompt_display_formatted = str(prompt_display)

        return {
            "basic": {
                "request_id": event.request_id,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "provider": event.provider,
                "model": event.model,
                "session_id": event.session_id,
            },
            "fingerprint": {
                "hash": event.request_hash,
                "occurrences": len(group),
                "occurrence_number": occurrence_idx,
                "first_seen": group[0].timestamp.isoformat() if group and group[0].timestamp else None,
                "last_seen": group[-1].timestamp.isoformat() if group and group[-1].timestamp else None,
                "original_request_id": original_request_id if occurrence_idx > 1 else None,
            },
            "usage": {
                "input_tokens": event.input_tokens,
                "output_tokens": event.output_tokens,
                "total_tokens": event.total_tokens,
                "latency_ms": round(event.latency_ms, 2),
                "estimated_cost_usd": self._round_cost(cost, 6),
            },
            "content": {
                "prompt": prompt_display_formatted,
                "response": event.response or "(None)",
            },
            "duplicate_status": {
                "is_duplicate": occurrence_idx > 1,
                "status_label": "Repeated Request" if occurrence_idx > 1 else "Unique Request",
                "occurrence_text": f"Occurrence #{occurrence_idx} of {len(group)} with this fingerprint",
            },
            "metadata": event.metadata or {},
        }

    def get_fingerprints(
        self,
        search: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        sort_by: str = "occurrences",  # 'occurrences', 'tokens', 'cost', 'last_seen'
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Aggregate and analyze request fingerprints."""
        all_events = self._get_all_events()
        groups = self._index_fingerprints(all_events)

        records = []
        total_unique_fps = len(groups)
        repeated_fps_count = 0
        total_wasted_tokens = 0
        total_wasted_costs: List[Optional[float]] = []

        for h, evts in groups.items():
            occurrences = len(evts)
            if occurrences > 1:
                repeated_fps_count += 1
                repeats = evts[1:]
                total_wasted_tokens += sum(e.total_tokens for e in repeats)
                for e in repeats:
                    total_wasted_costs.append(self._calculate_event_cost(e))

            first_evt = evts[0]
            last_evt = evts[-1]
            tot_tokens = sum(e.total_tokens for e in evts)
            tot_cost = self._sum_costs([self._calculate_event_cost(e) for e in evts])
            savings_cost = self._sum_costs([self._calculate_event_cost(e) for e in evts[1:]]) if occurrences > 1 else None

            # Prompt snippet
            p = first_evt.prompt
            if isinstance(p, list):
                preview = " ".join([str(m.get("content", "")) for m in p if isinstance(m, dict)])
            else:
                preview = str(p)
            preview = (preview[:100] + "...") if len(preview) > 100 else preview

            record = {
                "fingerprint": h,
                "occurrences": occurrences,
                "duplicate_count": occurrences - 1,
                "first_seen": first_evt.timestamp.isoformat() if first_evt.timestamp else None,
                "last_seen": last_evt.timestamp.isoformat() if last_evt.timestamp else None,
                "model": first_evt.model,
                "provider": first_evt.provider,
                "prompt_preview": preview,
                "total_tokens": tot_tokens,
                "estimated_cost_usd": self._round_cost(tot_cost, 5),
                "potential_savings_tokens": sum(e.total_tokens for e in evts[1:]) if occurrences > 1 else 0,
                "potential_savings_cost_usd": self._round_cost(savings_cost, 5),
            }

            # Filter
            if provider and provider != "all" and record["provider"].lower() != provider.lower():
                continue
            if model and model != "all" and record["model"].lower() != model.lower():
                continue
            if search:
                s = search.lower()
                if not (s in h.lower() or s in preview.lower() or s in record["model"].lower()):
                    continue

            records.append(record)

        # Sorting
        reverse = sort_order.lower() == "desc"
        if sort_by == "tokens":
            records.sort(key=lambda x: x["total_tokens"], reverse=reverse)
        elif sort_by == "cost":
            records.sort(
                key=lambda x: (x["estimated_cost_usd"] is None, x["estimated_cost_usd"] or 0.0),
                reverse=reverse,
            )
        elif sort_by == "last_seen":
            records.sort(key=lambda x: x["last_seen"] or "", reverse=reverse)
        elif sort_by == "savings":
            records.sort(key=lambda x: x["potential_savings_tokens"], reverse=reverse)
        else:  # occurrences
            records.sort(key=lambda x: x["occurrences"], reverse=reverse)

        paginated = records[offset : offset + limit]

        total_wasted_cost = self._sum_costs(total_wasted_costs)

        return {
            "total": len(records),
            "summary": {
                "unique_fingerprints": total_unique_fps,
                "repeated_fingerprints": repeated_fps_count,
                "potential_savings_tokens": total_wasted_tokens,
                "potential_savings_cost_usd": self._round_cost(total_wasted_cost, 4),
            },
            "fingerprints": paginated,
        }

    def get_models_comparison(self) -> Dict[str, Any]:
        """Aggregate model performance and cost metrics without ranking or declaring winners."""
        all_events = self._get_all_events()
        groups: Dict[str, List[RequestEvent]] = defaultdict(list)
        for e in all_events:
            groups[e.model].append(e)

        models_list: List[Dict[str, Any]] = []
        for model_name, evts in groups.items():
            lat_stats = self.latency_analyzer.analyze(evts)
            cost_est = self.cost_calculator.estimate(evts)
            token_stats = self.token_analyzer.analyze(evts)

            # Duplicates for this model
            fp_groups = self._index_fingerprints(evts)
            dups = sum(len(g) - 1 for g in fp_groups.values() if len(g) > 1)
            dup_rate = (dups / len(evts) * 100) if evts else 0.0

            models_list.append({
                "model": model_name,
                "provider": evts[0].provider if evts else "unknown",
                "requests": len(evts),
                "input_tokens": token_stats.total_input_tokens,
                "output_tokens": token_stats.total_output_tokens,
                "total_tokens": token_stats.total_tokens,
                "avg_latency_ms": round(lat_stats.avg_latency_ms, 1),
                "p50_latency_ms": round(lat_stats.p50_latency_ms, 1),
                "p95_latency_ms": round(lat_stats.p95_latency_ms, 1),
                "p99_latency_ms": round(lat_stats.p99_latency_ms, 1),
                "estimated_cost_usd": self._round_cost(cost_est.total_cost_usd, 4),
                "duplicate_count": dups,
                "duplicate_rate_pct": round(dup_rate, 1),
            })

        # Sort naturally by request count descending (standard table default)
        models_list.sort(key=lambda x: x["requests"], reverse=True)

        return {
            "total_models": len(models_list),
            "models": models_list,
        }

    def get_analytics(self, time_range: str = "all") -> Dict[str, Any]:
        """Detailed analytical views for request volume, tokens, cost, latency, and efficiency."""
        all_events = self._get_all_events()
        events = self._filter_events_by_time(all_events, time_range)

        # 1. Timeline series (volume, tokens, cost, unique vs repeated)
        timeline: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "requests": 0,
                "unique_requests": 0,
                "repeated_requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "costs": [],
                "latencies": [],
            }
        )

        date_format = "%Y-%m-%d %H:00" if time_range in ("24h",) else "%Y-%m-%d"
        sorted_events = sorted(events, key=lambda x: x.timestamp or datetime.min.replace(tzinfo=timezone.utc))

        seen_hashes = set()
        for e in sorted_events:
            ts = e.timestamp or datetime.now(timezone.utc)
            bucket = ts.strftime(date_format)
            timeline[bucket]["requests"] += 1
            timeline[bucket]["input_tokens"] += e.input_tokens
            timeline[bucket]["output_tokens"] += e.output_tokens
            timeline[bucket]["costs"].append(self._calculate_event_cost(e))
            timeline[bucket]["latencies"].append(e.latency_ms)

            if e.request_hash:
                if e.request_hash in seen_hashes:
                    timeline[bucket]["repeated_requests"] += 1
                else:
                    timeline[bucket]["unique_requests"] += 1
                    seen_hashes.add(e.request_hash)
            else:
                timeline[bucket]["unique_requests"] += 1

        labels = sorted(timeline.keys())
        requests_series = [timeline[k]["requests"] for k in labels]
        unique_series = [timeline[k]["unique_requests"] for k in labels]
        repeated_series = [timeline[k]["repeated_requests"] for k in labels]
        input_tokens_series = [timeline[k]["input_tokens"] for k in labels]
        output_tokens_series = [timeline[k]["output_tokens"] for k in labels]
        cost_series = [self._round_cost(self._sum_costs(timeline[k]["costs"]), 4) for k in labels]

        # Latency percentiles over time
        avg_latency_series = []
        for k in labels:
            lats = timeline[k]["latencies"]
            avg_latency_series.append(round(sum(lats) / len(lats), 1) if lats else 0.0)

        # 2. Provider distribution
        provider_counts: Dict[str, int] = defaultdict(int)
        provider_tokens: Dict[str, int] = defaultdict(int)
        provider_costs: Dict[str, List[Optional[float]]] = defaultdict(list)
        for e in events:
            provider_counts[e.provider] += 1
            provider_tokens[e.provider] += e.total_tokens
            provider_costs[e.provider].append(self._calculate_event_cost(e))

        # 3. Model distribution
        model_counts: Dict[str, int] = defaultdict(int)
        model_tokens: Dict[str, int] = defaultdict(int)
        for e in events:
            model_counts[e.model] += 1
            model_tokens[e.model] += e.total_tokens

        # 4. Overall Efficiency Report using EcoTrace's EfficiencyAnalyzer
        fp_groups = self._index_fingerprints(events)
        dups = sum(len(g) - 1 for g in fp_groups.values() if len(g) > 1)
        lat_stats = self.latency_analyzer.analyze(events)
        dup_analysis = self.duplicate_detector.analyze(events)
        token_stats = self.token_analyzer.analyze(events)

        efficiency_report = self.efficiency_analyzer.analyze(
            events=events,
            duplicates=dup_analysis,
            tokens=token_stats,
            latency=lat_stats,
        )

        return {
            "timeline": {
                "labels": labels,
                "requests": requests_series,
                "unique_requests": unique_series,
                "repeated_requests": repeated_series,
                "input_tokens": input_tokens_series,
                "output_tokens": output_tokens_series,
                "cost": cost_series,
                "avg_latency": avg_latency_series,
            },
            "providers": {
                "labels": list(provider_counts.keys()),
                "requests": [provider_counts[k] for k in provider_counts],
                "tokens": [provider_tokens[k] for k in provider_counts],
                "cost": [self._round_cost(self._sum_costs(provider_costs[k]), 4) for k in provider_counts],
            },
            "models": {
                "labels": list(model_counts.keys()),
                "requests": [model_counts[k] for k in model_counts],
                "tokens": [model_tokens[k] for k in model_counts],
            },
            "efficiency": {
                "score": efficiency_report.efficiency_score,
                "total_requests": efficiency_report.total_requests,
                "duplicate_count": efficiency_report.duplicate_count,
                "estimated_wasted_tokens": efficiency_report.estimated_wasted_tokens,
                "unique_ratio": round((len(events) - dups) / len(events), 4) if events else 1.0,
                "recommendations": efficiency_report.recommendations,
            },
            "latency_summary": {
                "avg": round(lat_stats.avg_latency_ms, 1),
                "p50": round(lat_stats.p50_latency_ms, 1),
                "p95": round(lat_stats.p95_latency_ms, 1),
                "p99": round(lat_stats.p99_latency_ms, 1),
                "min": round(lat_stats.min_latency_ms, 1),
                "max": round(lat_stats.max_latency_ms, 1),
            },
        }

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Generate transparent, rule-based recommendations derived strictly from real data."""
        all_events = self._get_all_events()
        if not all_events:
            return []

        recommendations: List[Dict[str, Any]] = []

        # Rule 1: Overall Caching Opportunity via EcoTrace CachingStrategy
        caching_res = self.caching_strategy.evaluate(all_events)
        if caching_res.applicable:
            dups = caching_res.estimated_savings.get("duplicate_requests", 0)
            wasted_toks = caching_res.estimated_savings.get("tokens", 0)
            fp_groups = self._index_fingerprints(all_events)
            wasted_cost = self._sum_costs([
                self._calculate_event_cost(e)
                for g in fp_groups.values()
                if len(g) > 1
                for e in g[1:]
            ])

            cost_ev_text = f"${wasted_cost:.4f}" if wasted_cost is not None else "N/A"
            cost_imp_text = f"avoids ${wasted_cost:.4f} in duplicate API costs" if wasted_cost is not None else "avoids duplicate API costs"

            recommendations.append({
                "id": "rec_duplicate_caching",
                "category": "Caching & Latency",
                "priority": "High" if dups >= 5 else "Medium",
                "observation": f"Deterministic request analysis identified {dups} redundant execution(s) across identical request fingerprints.",
                "evidence": f"{dups} duplicate request occurrences detected; {wasted_toks:,} total tokens consumed unnecessarily; {cost_ev_text} estimated API expenditure on repeated calls.",
                "suggested_action": "Deploy response caching (e.g. in-memory LRU or Redis key-value store) indexed by deterministic SHA-256 request fingerprint with an application-specific TTL.",
                "expected_impact": f"Eliminates up to {wasted_toks:,} redundant tokens, {cost_imp_text}, and reduces response latency to ~0 ms for cache hits.",
                "confidence": "High (100% deterministic SHA-256 fingerprint match across recorded events)",
            })

        # Rule 2: Top individual high-frequency duplicate fingerprints
        fp_groups = self._index_fingerprints(all_events)
        high_freq_fps = [(h, g) for h, g in fp_groups.items() if len(g) > 2]
        high_freq_fps.sort(key=lambda x: len(x[1]), reverse=True)

        for idx, (h, group) in enumerate(high_freq_fps[:3]):
            cnt = len(group)
            repeats = group[1:]
            w_tokens = sum(e.total_tokens for e in repeats)
            w_cost = self._sum_costs([self._calculate_event_cost(e) for e in repeats])
            w_cost_str = f"${w_cost:.4f}" if w_cost is not None else "N/A"
            model_name = group[0].model
            p = group[0].prompt
            preview = str(p)[:80] + ("..." if len(str(p)) > 80 else "")

            recommendations.append({
                "id": f"rec_fingerprint_{h[:8]}",
                "category": "Prompt Specific Caching",
                "priority": "Medium",
                "observation": f"Fingerprint '{h[:12]}...' on model '{model_name}' was executed {cnt} times.",
                "evidence": f"{cnt} exact occurrences recorded. Prompt preview: '{preview}'. Total waste across repetitions: {w_tokens:,} tokens, {w_cost_str}.",
                "suggested_action": f"Pin or cache the static output for this prompt in the client application layer before dispatching to {model_name}.",
                "expected_impact": f"Directly saves ~{w_tokens:,} tokens and {w_cost_str} with zero risk of prompt drift.",
                "confidence": f"High ({cnt} exact matches recorded in local telemetry)",
            })

        # Rule 3: Latency Distribution & Tail Latency
        lat_stats = self.latency_analyzer.analyze(all_events)
        if lat_stats.request_count >= 5 and lat_stats.avg_latency_ms > 0:
            tail_ratio = lat_stats.p99_latency_ms / lat_stats.avg_latency_ms
            if tail_ratio >= 2.5:
                recommendations.append({
                    "id": "rec_tail_latency",
                    "category": "Performance & Reliability",
                    "priority": "Medium",
                    "observation": f"P99 latency ({lat_stats.p99_latency_ms:.1f} ms) is {tail_ratio:.1f}x higher than average latency ({lat_stats.avg_latency_ms:.1f} ms).",
                    "evidence": f"Avg: {lat_stats.avg_latency_ms:.1f} ms, P50: {lat_stats.p50_latency_ms:.1f} ms, P95: {lat_stats.p95_latency_ms:.1f} ms, P99: {lat_stats.p99_latency_ms:.1f} ms, Max: {lat_stats.max_latency_ms:.1f} ms across {lat_stats.request_count} requests.",
                    "suggested_action": "Set aggressive client timeouts with exponential backoff or enable streaming responses to decrease perceived time-to-first-token for long completions.",
                    "expected_impact": "Reduces worst-case wait times for the slowest 1-5% of user-facing requests.",
                    "confidence": f"High (Computed from distribution of {lat_stats.request_count} logged latency measurements)",
                })

        # Rule 4: Model Cost Concentration
        cost_by_model: Dict[str, List[Optional[float]]] = defaultdict(list)
        tokens_by_model: Dict[str, int] = defaultdict(int)
        for e in all_events:
            cost_by_model[e.model].append(self._calculate_event_cost(e))
            tokens_by_model[e.model] += e.total_tokens

        all_costs = [c for c_list in cost_by_model.values() for c in c_list]
        total_cost = self._sum_costs(all_costs)

        if total_cost is not None and total_cost > 0:
            for m_name, c_list in cost_by_model.items():
                m_cost = self._sum_costs(c_list)
                if m_cost is not None:
                    pct = (m_cost / total_cost) * 100
                    if pct >= 65 and len(cost_by_model) > 1:
                        recommendations.append({
                            "id": f"rec_cost_concentration_{m_name}",
                            "category": "Cost Management",
                            "priority": "Low",
                            "observation": f"Model '{m_name}' accounts for {pct:.1f}% of total estimated AI expenditure (${m_cost:.4f} of ${total_cost:.4f}).",
                            "evidence": f"{tokens_by_model[m_name]:,} total tokens consumed on {m_name}, generating ${m_cost:.4f} in estimated fees.",
                            "suggested_action": f"Review whether all requests routed to '{m_name}' strictly require its capabilities or if lightweight models (e.g. mini/flash variants) suffice for simple prompts.",
                            "expected_impact": "Potential 40-70% cost reduction on high-volume, low-complexity subtasks.",
                            "confidence": "Moderate (Requires domain evaluation of prompt complexity)",
                        })

        return recommendations

    def get_settings_info(self) -> Dict[str, Any]:
        """Fetch system, storage, and pricing configuration details."""
        storage_type = "SQLite" if isinstance(self.storage, SQLiteStorage) else "Memory"
        file_size_bytes = 0
        if os.path.exists(self.db_path):
            file_size_bytes = os.path.getsize(self.db_path)

        all_events = self._get_all_events()

        return {
            "storage": {
                "type": storage_type,
                "db_path": self.db_path,
                "file_size_bytes": file_size_bytes,
                "file_size_formatted": f"{file_size_bytes / 1024:.1f} KB" if file_size_bytes < 1048576 else f"{file_size_bytes / 1048576:.2f} MB",
                "total_events": len(all_events),
                "journal_mode": "WAL",
            },
            "pricing": self.cost_calculator._pricing,
            "environmental_constants": {
                "wh_per_1k_tokens": self.energy_estimator._rate,
                "grid_intensity_gco2_kwh": self.carbon_estimator._grid_intensity,
            },
        }

    def clear_database(self) -> None:
        """Clear all stored events from database."""
        self.storage.clear()

    def close(self) -> None:
        """Close storage resources."""
        if hasattr(self.storage, "close"):
            self.storage.close()

