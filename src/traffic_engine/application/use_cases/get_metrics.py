"""
GetMetrics use case implementation.

Retrieves current simulation performance metrics and optional historical trends
for monitoring and analysis purposes.
"""

import logging
from typing import List, Dict, Any, Optional

from ..contracts import GetMetricsRequest, GetMetricsResponse
from ...domain.simulation import SimulationModel
from ...domain.models import Metrics

logger = logging.getLogger(__name__)


class GetMetricsUseCase:
    """
    Use case for retrieving simulation performance metrics.
    
    Provides access to current simulation metrics and historical trends
    for performance monitoring, analysis, and optimization.
    """
    
    def __init__(self, simulation_model: SimulationModel):
        """
        Initialize use case with simulation model.
        
        Args:
            simulation_model: Active simulation model
        """
        self.simulation_model = simulation_model
        self._metrics_history: List[Dict[str, Any]] = []
        self._max_history_length = 1000  # Keep last 1000 ticks
    
    def execute(
        self, 
        simulation_id: str,
        request: GetMetricsRequest
    ) -> GetMetricsResponse:
        """
        Execute get metrics use case.
        
        Args:
            simulation_id: Identifier of simulation
            request: Metrics request parameters
            
        Returns:
            Response with current metrics and optional history
        """
        try:
            logger.info(f"Retrieving metrics for simulation {simulation_id}")
            
            # Get current simulation state and metrics
            current_state = self.simulation_model.get_state()
            current_metrics_obj = self.simulation_model.get_metrics()
            
            # Convert to dictionary format
            current_metrics = self._metrics_to_dict(current_metrics_obj)
            
            # Update metrics history
            self._update_history(current_metrics)
            
            # Prepare historical data if requested
            history = None
            if request.include_history:
                history = self._get_history_window(request.window_ticks)
            
            logger.debug(f"Retrieved metrics for tick {current_state.tick}")
            
            return GetMetricsResponse(
                simulation_id=simulation_id,
                current_metrics=current_metrics,
                history=history,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error retrieving metrics for simulation {simulation_id}: {e}")
            return GetMetricsResponse(
                simulation_id=simulation_id,
                current_metrics={},
                history=None,
                success=False,
                error=f"Failed to retrieve metrics: {str(e)}"
            )
    
    def _metrics_to_dict(self, metrics: Metrics) -> Dict[str, Any]:
        """
        Convert Metrics object to dictionary using the current domain contract.
        
        Args:
            metrics: Metrics object from simulation
            
        Returns:
            Complete dictionary representation of metrics
        """
        base_metrics = {
            'tick': metrics.tick,
            'timestamp': self._get_timestamp(),
            'total_vehicles': metrics.total_vehicles,
            'avg_speed_kmh': metrics.avg_speed_kmh,
            'density': metrics.density,
            'throughput_veh_per_min': metrics.throughput_veh_per_min,
            'congestion_ratio': metrics.congestion_ratio,
            'boundary_inflow': metrics.boundary_inflow,
            'boundary_outflow': metrics.boundary_outflow,
        }

        base_metrics['performance_grade'] = self._classify_performance(base_metrics)
        
        return base_metrics
    
    def _update_history(self, current_metrics: Dict[str, Any]) -> None:
        """
        Update internal metrics history with current values.
        
        Args:
            current_metrics: Current metrics dictionary
        """
        # Add to history
        self._metrics_history.append(current_metrics.copy())
        
        # Maintain maximum history length
        if len(self._metrics_history) > self._max_history_length:
            self._metrics_history.pop(0)
    
    def _get_history_window(self, window_ticks: int) -> List[Dict[str, Any]]:
        """
        Get metrics history for specified window.
        
        Args:
            window_ticks: Number of recent ticks to include
            
        Returns:
            List of metrics dictionaries for the window
        """
        if window_ticks <= 0:
            return []
        
        return self._metrics_history[-window_ticks:] if self._metrics_history else []
    
    def _classify_performance(self, metrics: Dict[str, Any]) -> str:
        """
        Classify overall simulation performance.
        
        Args:
            metrics: Current metrics dictionary
            
        Returns:
            Performance grade: "excellent", "good", "fair", "poor"
        """
        # Calculate performance score based on multiple factors
        score = 0.0
        
        avg_speed = metrics.get('avg_speed_kmh', 0.0)
        if avg_speed > 40.0:
            score += 30
        elif avg_speed > 25.0:
            score += 20
        elif avg_speed > 10.0:
            score += 10
        
        # Congestion factor (lower is better)
        congestion_ratio = metrics.get('congestion_ratio', 1.0)
        if congestion_ratio < 0.2:
            score += 30
        elif congestion_ratio < 0.4:
            score += 20
        elif congestion_ratio < 0.6:
            score += 10
        
        density = metrics.get('density', 0.0)
        if 0.2 <= density <= 0.6:
            score += 25
        elif 0.1 <= density <= 0.8:
            score += 15
        elif density > 0:
            score += 5
        
        throughput = metrics.get('throughput_veh_per_min', 0.0)
        if throughput > 30.0:
            score += 15
        elif throughput > 10.0:
            score += 10
        elif throughput > 0.0:
            score += 5
        
        # Classify based on total score
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "poor"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for metrics."""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def get_performance_summary(self, simulation_id: str) -> Dict[str, Any]:
        """
        Get a high-level performance summary.
        
        Args:
            simulation_id: Simulation identifier
            
        Returns:
            Summary of key performance indicators
        """
        if not self._metrics_history:
            return {'status': 'no_data'}
        
        recent_metrics = self._metrics_history[-10:]  # Last 10 ticks
        
        return {
            'status': 'active',
            'duration_ticks': len(self._metrics_history),
            'recent_avg_speed_kmh': sum(m.get('avg_speed_kmh', 0) for m in recent_metrics) / len(recent_metrics),
            'recent_congestion': sum(m.get('congestion_ratio', 0) for m in recent_metrics) / len(recent_metrics),
            'peak_vehicles': max(m.get('total_vehicles', 0) for m in self._metrics_history),
            'current_throughput_veh_per_min': self._metrics_history[-1].get('throughput_veh_per_min', 0) if self._metrics_history else 0,
            'current_grade': recent_metrics[-1].get('performance_grade', 'unknown') if recent_metrics else 'unknown'
        }