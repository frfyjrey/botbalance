"""
URL patterns for trading strategies API.
"""

from django.urls import path

from . import views

app_name = "strategies"

urlpatterns = [
    # Strategy management
    path("", views.user_strategy_view, name="user_strategy"),
    path("activate/", views.strategy_activate_view, name="strategy_activate"),
    path("constants/", views.strategy_constants_view, name="strategy_constants"),
    # Rebalancing
    path("rebalance/plan/", views.rebalance_plan_view, name="rebalance_plan"),
    path("rebalance/execute/", views.rebalance_execute_view, name="rebalance_execute"),
]
