from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import render, redirect
from urllib.parse import urlencode
import requests
import logging
import json

# Configuración de logs y modelo de usuario
logger = logging.getLogger(__name__)
User = get_user_model()

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def google_oauth_callback(request):
    """
    Endpoint que recibe el código de autorización de Google
    y devuelve tokens JWT de nuestra aplicación.
    """
    
    # 1. Obtener el código de autorización (de POST o GET)
    code = request.data.get('code') or request.query_params.get('code')
    
    if not code:
        error_msg = 'El código de autorización es requerido'
        logger.error(error_msg)
        return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 2. Configuración dinámica de la URI de redirección
        # Detecta si estamos en Local (127.0.0.1) o en Producción (PythonAnywhere)
        redirect_uri = getattr(settings, 'OAUTH_REDIRECT_URI', 'http://127.0.0.1:8000/api/auth/google/callback/')
        
        # 3. Intercambiar código por access token de Google
        token_url = 'https://oauth2.googleapis.com/token'
        google_config = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']
        
        token_data = {
            'code': code,
            'client_id': google_config['client_id'],
            'client_secret': google_config['secret'],
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        logger.info(f"Intercambiando código con Google usando URI: {redirect_uri}")
        token_response = requests.post(token_url, data=token_data, timeout=10)
        token_response.raise_for_status()
        
        tokens = token_response.json()
        google_access_token = tokens.get('access_token')
        
        if not google_access_token:
            error_msg = 'No se pudo obtener access token de Google'
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_401_UNAUTHORIZED)
        
        # 4. Obtener información del usuario desde Google
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {google_access_token}'}
        
        userinfo_response = requests.get(userinfo_url, headers=headers, timeout=10)
        userinfo_response.raise_for_status()
        user_data = userinfo_response.json()
        
        logger.info(f"Datos recibidos de Google para el usuario: {user_data.get('email')}")
        
        # 5. Crear o actualizar usuario en Django
        email = user_data.get('email')
        if not email:
            return Response({'error': 'Email no proporcionado por Google'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Lógica de sincronización de usuario
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': user_data.get('given_name', ''),
                'last_name': user_data.get('family_name', ''),
            }
        )
        
        # Actualizar datos si el usuario ya existía
        if not created:
            user.first_name = user_data.get('given_name', user.first_name)
            user.last_name = user_data.get('family_name', user.last_name)
            user.save()
        
        # 6. Generar tokens JWT (SimpleJWT)
        refresh = RefreshToken.for_user(user)
        
        # 7. Respuesta estructurada para el frontend
        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "google_data": {
                "picture": user_data.get('picture'),
                "verified_email": user_data.get('verified_email'),
            },
            "message": "Login exitoso con Google" if not created else "Cuenta creada con Google"
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error de Google API: {e.response.text}")
        return Response({'error': 'Error en la autenticación con Google', 'details': e.response.json()}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return Response({'error': 'Error interno del servidor', 'msg': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def google_oauth_redirect(request):
    """
    Endpoint que genera la URL de autorización y redirige a Google.
    """
    try:
        google_config = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']
        scopes = settings.SOCIALACCOUNT_PROVIDERS['google']['SCOPE']
        
        # Detección dinámica de la URI
        redirect_uri = getattr(settings, 'OAUTH_REDIRECT_URI', 'http://127.0.0.1:8000/api/auth/google/callback/')
        
        params = {
            'client_id': google_config["client_id"],
            'redirect_uri': redirect_uri,
            'scope': " ".join(scopes),
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
        }
        
        auth_url = f'https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}'
        
        # Devolvemos la URL para que el frontend pueda manejar la redirección
        return Response({'auth_url': auth_url}, status=status.HTTP_200_OK)
    
    except KeyError:
        return Response({'error': 'Configuración de Google no encontrada en settings'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)