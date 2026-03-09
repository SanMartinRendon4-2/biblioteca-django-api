from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from urllib.parse import urlencode
import requests
import logging
from django.shortcuts import render, redirect
import urllib.parse
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
    
    GET /api/auth/google/callback/?code=4/0AbUR2VN...
    o
    POST /api/auth/google/callback/
    Body: { "code": "4/0AbUR2VN..." }
    """
    
    # 1. Obtener el código de autorización (de POST o GET)
    code = request.data.get('code') or request.query_params.get('code')
    
    if not code:
        error_msg = 'El código de autorización es requerido'
        logger.error(error_msg)
        # Si es una petición de navegador, devolvemos error en JSON para que se vea en la API
        return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 2. Intercambiar código por access token de Google
        token_url = 'https://oauth2.googleapis.com/token'
        google_config = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']
        
        token_data = {
            'code': code,
            'client_id': google_config['client_id'],
            'client_secret': google_config['secret'],
            'redirect_uri': 'http://127.0.0.1:8000/api/auth/google/callback/',
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data, timeout=10)
        token_response.raise_for_status()
        
        tokens = token_response.json()
        google_access_token = tokens.get('access_token')
        
        if not google_access_token:
            error_msg = 'No se pudo obtener access token de Google'
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_401_UNAUTHORIZED)
        
        logger.info(f"Access token de Google obtenido: {google_access_token[:20]}...")
        
        # 3. Obtener información del usuario de Google
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {google_access_token}'}
        
        userinfo_response = requests.get(userinfo_url, headers=headers, timeout=10)
        userinfo_response.raise_for_status()
        user_data = userinfo_response.json()
        
        logger.info(f"Datos de usuario de Google: {user_data}")
        
        # 4. Crear o actualizar usuario en Django
        email = user_data.get('email')
        
        if not email:
            error_msg = 'No se pudo obtener el email del usuario'
            logger.error(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Buscar si el usuario ya existe (usando la parte antes del @ como username)
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': user_data.get('given_name', ''),
                'last_name': user_data.get('family_name', ''),
            }
        )
        
        # Actualizar información si ya existía
        if not created:
            user.first_name = user_data.get('given_name', user.first_name)
            user.last_name = user_data.get('family_name', user.last_name)
            user.save()
            logger.info(f"Usuario existente actualizado: {user.email}")
        else:
            logger.info(f"Nuevo usuario creado: {user.email}")
        
        # 5. Generar tokens JWT de nuestra aplicación
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # 6. Preparar RESPUESTA FINAL (Estructura idéntica a tu imagen)
        response_data = {
            "access": access_token,
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
            },
            "google_data": {
                "picture": user_data.get('picture'),
                "verified_email": user_data.get('verified_email'),
            },
            "message": "Login exitoso con Google" if not created else "Cuenta creada exitosamente con Google"
        }
        
        # Devolvemos el Response para que se vea el JSON en el navegador
        return Response(response_data, status=status.HTTP_200_OK)
    
    except requests.Timeout:
        logger.error("Timeout al comunicarse con Google")
        return Response({'error': 'Timeout al comunicarse con Google'}, status=status.HTTP_408_REQUEST_TIMEOUT)
    
    except requests.RequestException as e:
        logger.error(f"Error al comunicarse con Google: {str(e)}")
        return Response({'error': f'Error de comunicación con Google: {str(e)}'}, status=status.HTTP_401_UNAUTHORIZED)
    
    except Exception as e:
        logger.error(f"Error inesperado en OAuth: {str(e)}")
        return Response({'error': f'Error inesperado: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def google_oauth_redirect(request):
    """
    Endpoint que redirige al usuario a Google para autorización.
    """
    google_config = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']
    scopes = settings.SOCIALACCOUNT_PROVIDERS['google']['SCOPE']
    
    # Construir parámetros para la URL de Google
    params = {
        'client_id': google_config["client_id"],
        'redirect_uri': 'http://127.0.0.1:8000/api/auth/google/callback/',
        'scope': " ".join(scopes),
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent',
    }
    
    auth_url = f'https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}'
    
    return Response({'auth_url': auth_url}, status=status.HTTP_200_OK)