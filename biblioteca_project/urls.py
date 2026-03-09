from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from libros.jwt_views import CustomTokenObtainPairView
from libros import web_views  # ← AGREGAR
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('admin/', admin.site.urls),
    path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True))),
    # 🔐 Endpoints de Autenticación JWT (SimpleJWT)
    path('api/auth/jwt/login/', CustomTokenObtainPairView.as_view(), name='jwt_login'),
    path('api/auth/jwt/refresh/', TokenRefreshView.as_view(), name='jwt_refresh'),

    # 🌐 Autenticación Social (Google / Allauth)
    # Esto habilitará rutas como /accounts/google/login/
    path('accounts/', include('allauth.urls')),

    # 🛡️ OAuth2 Provider (Django OAuth Toolkit)
    # Útil si vas a registrar aplicaciones externas
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    # 📚 URLs de tu lógica de negocio (App libros)
    path('api/', include('libros.api_urls')),

# URLs de páginas web (para pruebas)
    path('', web_views.home, name='home'),
    path('oauth/login/', web_views.oauth_login, name='oauth_login'),
    path('login/jwt/', web_views.jwt_login_page, name='jwt_login_page'),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]