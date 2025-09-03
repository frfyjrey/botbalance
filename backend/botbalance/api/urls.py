"""
API URL patterns for the botbalance project.
"""

from django.urls import include, path

from . import views

app_name = "api"

# Authentication URLs
auth_patterns = [
    path("login/", views.login_view, name="login"),
    path("profile/", views.user_profile_view, name="profile"),
]

# Task management URLs
task_patterns = [
    path("echo/", views.create_echo_task_view, name="create_echo_task"),
    path("heartbeat/", views.create_heartbeat_task_view, name="create_heartbeat_task"),
    path("long/", views.create_long_task_view, name="create_long_task"),
    path("status/", views.task_status_view, name="task_status"),
    path("list/", views.list_tasks_view, name="list_tasks"),
]

# User account management URLs
me_patterns = [
    path("balances/", views.user_balances_view, name="balances"),
    path("portfolio/summary/", views.portfolio_summary_view, name="portfolio_summary"),
    path(
        "portfolio/snapshots/",
        views.portfolio_snapshots_list_view,
        name="portfolio_snapshots_list",
    ),
    path(
        "portfolio/snapshots/create/",
        views.create_portfolio_snapshot_view,
        name="create_portfolio_snapshot",
    ),
    path(
        "portfolio/snapshots/delete_all/",
        views.delete_all_portfolio_snapshots_view,
        name="delete_all_portfolio_snapshots",
    ),
    path(
        "portfolio/last_snapshot/",
        views.latest_portfolio_snapshot_view,
        name="latest_portfolio_snapshot",
    ),
    path("strategy/", include("strategies.urls", namespace="strategy")),
]

urlpatterns = [
    # System endpoints
    path("health/", views.health_check_view, name="health"),
    path("version/", views.version_view, name="version"),
    # Authentication endpoints
    path("auth/", include((auth_patterns, "auth"))),
    # Task management endpoints
    path("tasks/", include((task_patterns, "tasks"))),
    # User account endpoints
    path("me/", include((me_patterns, "me"))),
]
