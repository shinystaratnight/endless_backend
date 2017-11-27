from django.conf.urls import url

from r3sourcer.apps.company_settings import views


urlpatterns = [
    url(r'^permissions/all/$', views.GlobalPermissionListView.as_view(), name='global_permission_list'),
    url(r'^permissions/user/(?P<id>[\w\-]+)/set/$', views.SetUserGlobalPermissionView.as_view(), name='set_user_global_permission'),
    url(r'^permissions/user/(?P<id>[\w\-]+)/revoke/$', views.RevokeUserGlobalPermissionView.as_view(), name='revoke_user_global_permission'),
    url(r'^permissions/user/(?P<id>[\w\-]+)/$', views.UserGlobalPermissionListView.as_view(), name='user_global_permission_list'),
    url(r'^permissions/user/(?P<id>[\w\-]+)/groups/$', views.UserGroupListView.as_view(), name='user_group_list'),
    url(r'^permissions/group/(?P<id>[\w\-]+)/add_user/$', views.AddUserToGroupView.as_view(), name='add_user_to_group'),
    url(r'^permissions/group/(?P<id>[\w\-]+)/remove_user/$', views.RemoveUserFromGroupView.as_view(), name='remove_user_from_group'),
    url(r'^permissions/group/(?P<id>[\w\-]+)/set/$', views.SetGroupGlobalPermissionView.as_view(), name='set_group_global_permission'),
    url(r'^permissions/group/(?P<id>[\w\-]+)/delete/$', views.CompanyGroupDeleteView.as_view(), name='company_group_delete'),
    url(r'^permissions/group/(?P<id>[\w\-]+)/revoke/$', views.RevokeGroupGlobalPermissionView.as_view(), name='revoke_group_global_permission'),
    url(r'^permissions/group/(?P<id>[\w\-]+)/$', views.GroupGlobalPermissionListView.as_view(), name='group_global_permission_list'),
    url(r'^permissions/groups/create/$', views.CompanyGroupCreateView.as_view(), name='company_group_create'),
    url(r'^permissions/groups/$', views.CompanyGroupListView.as_view(), name='company_group_list'),
    url(r'^company_settings/users/$', views.CompanyUserListView.as_view(), name='company_users_list'),
]