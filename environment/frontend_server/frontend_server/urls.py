"""frontend_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

from translator import views as translator_views
from translator import api_views

urlpatterns = [
    # ==========================================================================
    # Frontend Web Views
    # ==========================================================================
    url(r'^$', translator_views.landing, name='landing'),
    url(r'^simulator_home$', translator_views.home, name='home'),
    url(r'^demo/(?P<sim_code>[\w-]+)/(?P<step>[\w-]+)/(?P<play_speed>[\w-]+)/$', translator_views.demo, name='demo'),
    url(r'^replay/(?P<sim_code>[\w-]+)/(?P<step>[\w-]+)/$', translator_views.replay, name='replay'),
    url(r'^replay_persona_state/(?P<sim_code>[\w-]+)/(?P<step>[\w-]+)/(?P<persona_name>[\w-]+)/$', translator_views.replay_persona_state, name='replay_persona_state'),
    url(r'^process_environment/$', translator_views.process_environment, name='process_environment'),
    url(r'^update_environment/$', translator_views.update_environment, name='update_environment'),
    url(r'^path_tester/$', translator_views.path_tester, name='path_tester'),
    url(r'^path_tester_update/$', translator_views.path_tester_update, name='path_tester_update'),
    path('admin/', admin.site.urls),
    
    # ==========================================================================
    # Health Check Endpoints
    # ==========================================================================
    path('health', api_views.api_health, name='health'),
    path('api/v1/health', api_views.api_health, name='api_health'),
    path('api/v1/health/detailed', api_views.api_health_detailed, name='api_health_detailed'),
    
    # ==========================================================================
    # External Agent REST API (v1)
    # ==========================================================================
    
    # Simulation status and control
    path('api/v1/simulation/status', api_views.api_simulation_status, name='api_simulation_status'),
    path('api/v1/simulations', api_views.api_list_simulations, name='api_list_simulations'),
    path('api/v1/scenarios', api_views.api_list_scenarios, name='api_list_scenarios'),
    
    # Agent management
    path('api/v1/agents', api_views.api_list_agents, name='api_list_agents'),
    path('api/v1/agents/<str:agent_name>/state', api_views.api_agent_state, name='api_agent_state'),
    path('api/v1/agents/<str:agent_name>/memory', api_views.api_agent_memory, name='api_agent_memory'),
    path('api/v1/agents/<str:agent_name>/whisper', api_views.api_agent_whisper, name='api_agent_whisper'),
    path('api/v1/agents/<str:agent_name>/relationships', api_views.api_agent_relationships, name='api_agent_relationships'),
    
    # World state
    path('api/v1/world/snapshot', api_views.api_world_snapshot, name='api_world_snapshot'),
    
    # Agent templates
    path('api/v1/agent-templates', api_views.api_list_agent_templates, name='api_list_agent_templates'),
    
    # Multi-agent interaction features
    path('api/v1/broadcast', api_views.api_broadcast_goal, name='api_broadcast_goal'),
    path('api/v1/interactions', api_views.api_interaction_history, name='api_interaction_history'),
    path('api/v1/social-network', api_views.api_social_network, name='api_social_network'),
]
