"""
Vistas para predicciones de IA
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncDate
import json
import logging
import threading
from datetime import datetime, timedelta
from collections import defaultdict
from django.utils import timezone

from football_data.models import League, Match
from .models import PredictionModel, PredictionResult, TeamStats, SavedPrediction
from .services import PredictionService
from .multi_models import MultiModelPredictionService
from .advanced_models import AdvancedStatisticalModels
from .model_validation import ModelValidator
from .simple_models import SimplePredictionService, ModeloHibridoCorners, ModeloHibridoGeneral
from .model_trainer import ModelTrainer
from .forms import PredictionForm

logger = logging.getLogger('ai_predictions')


def convert_numpy_to_native(obj):
    """
    Convierte tipos numpy a tipos nativos de Python para serialización JSON.
    """
    import numpy as np
    
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_native(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_native(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_to_native(item) for item in obj)
    else:
        return obj


def process_predictions_background(session_key, home_team, away_team, league_id, league_name):
    """Procesa predicciones en segundo plano"""
    from django.contrib.sessions.backends.db import SessionStore
    
    try:
        logger.info(f"🔄 BACKGROUND INICIADO - Home: '{home_team}' vs Away: '{away_team}', Liga: {league_name}")
        session = SessionStore(session_key=session_key)
        league = League.objects.get(id=league_id)
        
        # No limpiar predicción anterior aquí - puede causar condición de carrera
        
        prediction_types = [
            'shots_total', 'shots_home', 'shots_away',
            'shots_on_target_total',
            'goals_total', 'goals_home', 'goals_away',
            'corners_total', 'corners_home', 'corners_away',
            'both_teams_score'
        ]
        
        all_predictions_by_type = {}
        total_types = len(prediction_types)
        
        logger.info("Generando predicciones en background...")
        logger.info(f"🔧 INICIANDO BUCLE - Home: '{home_team}' vs Away: '{away_team}', Liga: {league_name}")
        
        # LIMPIAR SESIÓN PARA FORZAR REGENERACIÓN
        session.pop('all_predictions', None)
        session.pop('prediction_data', None)
        session.modified = True
        session.save()
        logger.info("🔧 SESIÓN LIMPIADA - Forzando regeneración completa")
        
        # Procesamiento sin timeout (Windows compatible)
        logger.info(f"🔧 INICIANDO BUCLE - Total tipos: {total_types}")
        logger.info(f"🔧 TIPOS DE PREDICCIÓN: {prediction_types}")
        
        for index, pred_type in enumerate(prediction_types):
            try:
                logger.info(f"Procesando: {pred_type}")
                logger.info(f"🔧 ITERACIÓN {index+1}/{total_types} - {pred_type}")
                
                # Log específico para detectar si shots se procesa
                if 'shots' in pred_type:
                    logger.info(f"🎯 PROCESANDO SHOTS: {pred_type}")
                    logger.info(f"🎯 SHOTS DETECTADO - Iniciando procesamiento para {pred_type}")
            
                # Actualizar progreso
                session['prediction_progress'] = {
                    'current': index + 1,
                    'total': total_types,
                    'current_type': pred_type.replace('_', ' ').title(),
                    'status': 'processing'
                }
                session.modified = True
                session.save()
                
                simple_service = SimplePredictionService()
                trainer = ModelTrainer()
                
                # Generar modelos simples (3 modelos: Dixon-Coles/Poisson, Average, Ensemble)
                logger.info(f"Generando modelos simples para {pred_type}...")
                logger.info(f"🔧 PROCESANDO {pred_type} - Home: '{home_team}' vs Away: '{away_team}'")
                
                # MANEJO ESPECIAL PARA REMATES - USAR AMBOS MODELOS
                if 'shots' in pred_type or 'remates' in pred_type:
                    logger.info(f"🎯 ENTRANDO A MANEJO ESPECIAL DE REMATES (AMBOS MODELOS) para {pred_type}")
                    predictions = []
                    
                    try:
                        # Modelo 1: Shots Prediction Model (original)
                        from .shots_prediction_model import shots_prediction_model
                        logger.info(f"🎯 IMPORTACIÓN EXITOSA de shots_prediction_model para {pred_type}")
                        
                        if pred_type == 'shots_total':
                            pred1 = shots_prediction_model.predict_shots_total(home_team, away_team, league)
                        elif pred_type == 'shots_home':
                            pred1 = shots_prediction_model.predict_shots_home(home_team, away_team, league)
                        elif pred_type == 'shots_away':
                            pred1 = shots_prediction_model.predict_shots_away(home_team, away_team, league)
                        elif pred_type == 'shots_on_target_total':
                            pred1 = shots_prediction_model.predict_shots_on_target_total(home_team, away_team, league)
                        else:
                            pred1 = None
                        
                        if pred1:
                            predictions.append(pred1)
                            logger.info(f"🎯 MODELO 1 (Shots Prediction) agregado para {pred_type}")
                        
                    except Exception as e:
                        logger.error(f"❌ ERROR EN shots_prediction_model para {pred_type}: {e}")
                    
                    try:
                        # Modelo 2: XG Shots Model (nuevo)
                        from .xg_shots_model import xg_shots_model
                        logger.info(f"🎯 IMPORTACIÓN EXITOSA de xg_shots_model para {pred_type}")
                        
                        if pred_type == 'shots_total':
                            pred2 = xg_shots_model.predict_shots_total(home_team, away_team, league)
                        elif pred_type == 'shots_home':
                            pred2 = xg_shots_model.predict_shots_home(home_team, away_team, league)
                        elif pred_type == 'shots_away':
                            pred2 = xg_shots_model.predict_shots_away(home_team, away_team, league)
                        elif pred_type == 'shots_on_target_total':
                            pred2 = xg_shots_model.predict_shots_on_target_total(home_team, away_team, league)
                        else:
                            pred2 = None
                        
                        if pred2:
                            predictions.append(pred2)
                            logger.info(f"🎯 MODELO 2 (XG Shots) agregado para {pred_type}")
                        
                    except Exception as e:
                        logger.error(f"❌ ERROR EN xg_shots_model para {pred_type}: {e}")
                    
                    logger.info(f"🎯 TOTAL MODELOS DE REMATES para {pred_type}: {len(predictions)} modelos")
                    logger.info(f"🎯 PREDICCIONES GENERADAS: {predictions}")
                else:
                    try:
                        predictions = simple_service.get_all_simple_predictions(home_team, away_team, league, pred_type)
                        logger.info(f"✅ Modelos simples generados para {pred_type}: {len(predictions)}")
                    except Exception as e:
                        logger.error(f"❌ ERROR EN get_all_simple_predictions para {pred_type}: {e}")
                        logger.error(f"❌ TRACEBACK:", exc_info=True)
                        # Crear predicción de fallback
                        predictions = [{
                            'model_name': f'Fallback {pred_type}',
                            'prediction': 10.0,
                            'confidence': 0.3,
                            'probabilities': {'over_10': 0.5},
                            'total_matches': 0,
                            'error': str(e)
                        }]
                        logger.info(f"🔄 Usando predicción de fallback para {pred_type}")
                
                # Manejo específico para "both_teams_score" con modelo mejorado
                if pred_type == 'both_teams_score':
                    try:
                        from .enhanced_both_teams_score import enhanced_both_teams_score_model
                        enhanced_prob = enhanced_both_teams_score_model.predict(home_team, away_team, league)
                        
                        enhanced_prediction = {
                            'model_name': 'Enhanced Both Teams Score',
                            'prediction': enhanced_prob,
                            'confidence': 0.80,
                            'probabilities': {'both_score': enhanced_prob},
                            'total_matches': 100
                        }
                        predictions.append(enhanced_prediction)
                        logger.info(f"Modelo Enhanced Both Teams Score agregado para {pred_type}: {enhanced_prob:.3f}")
                    except Exception as e:
                        logger.error(f"Error en modelo mejorado ambos marcan: {e}")
                        # Fallback específico para ambos marcan
                        fallback_prob = 0.45  # Valor más realista que 0.5
                        enhanced_fallback = {
                            'model_name': 'Enhanced Both Teams Score (Fallback)',
                            'prediction': fallback_prob,
                            'confidence': 0.60,
                            'probabilities': {'both_score': fallback_prob},
                            'total_matches': 0
                        }
                        predictions.append(enhanced_fallback)
                        logger.info(f"Fallback ambos marcan agregado: {fallback_prob}")
                
                # Agregar modelo híbrido como modelo adicional para otros tipos
                elif 'corners' in pred_type:
                    try:
                        # Usar modelo híbrido especializado para corners
                        hybrid_model = ModeloHibridoCorners()
                        hybrid_prediction = hybrid_model.predecir(home_team, away_team, league, pred_type)
                        predictions.append(hybrid_prediction)
                        logger.info(f"Modelo Híbrido Corners agregado para {pred_type}")
                    except Exception as e:
                        logger.error(f"Error agregando modelo híbrido corners para {pred_type}: {e}")
                        # Crear modelo híbrido de fallback
                        hybrid_fallback = {
                            'model_name': 'Modelo Híbrido Corners',
                            'prediction': 10.0,
                            'confidence': 0.6,
                            'probabilities': {'over_10': 0.5, 'over_15': 0.3, 'over_20': 0.1},
                            'total_matches': 0,
                            'component_predictions': {}
                        }
                        predictions.append(hybrid_fallback)
                        logger.info(f"Modelo híbrido corners fallback agregado para {pred_type}")
                else:
                    try:
                        # Usar modelo híbrido general para otros tipos
                        hybrid_model = ModeloHibridoGeneral()
                        hybrid_prediction = hybrid_model.predecir(home_team, away_team, league, pred_type)
                        predictions.append(hybrid_prediction)
                        logger.info(f"Modelo Híbrido General agregado para {pred_type}")
                    except Exception as e:
                        logger.error(f"Error agregando modelo híbrido general para {pred_type}: {e}")
                        # Crear modelo híbrido de fallback
                        hybrid_fallback = {
                            'model_name': 'Modelo Híbrido General',
                            'prediction': 10.0,
                            'confidence': 0.6,
                            'probabilities': {'over_10': 0.5, 'over_15': 0.3, 'over_20': 0.1},
                            'total_matches': 0,
                            'component_predictions': {}
                        }
                        predictions.append(hybrid_fallback)
                        logger.info(f"Modelo híbrido general fallback agregado para {pred_type}")
                
                all_predictions_by_type[pred_type] = predictions
                model_names = [pred['model_name'] for pred in predictions]
                logger.info(f"[OK] {pred_type}: {len(predictions)} modelos generados - {model_names}")
                
            except Exception as e:
                logger.error(f"❌ ERROR EN {pred_type}: {e}")
                logger.error(f"❌ TRACEBACK:", exc_info=True)
                all_predictions_by_type[pred_type] = []
        
        # AGREGAR PREDICCIÓN OFICIAL (después de todos los otros modelos)
        logger.info("🎯 OFICIAL - Iniciando cálculo de predicción oficial en background")
        try:
            from .official_prediction_model import official_prediction_model
            all_predictions_by_type = official_prediction_model.add_to_predictions(all_predictions_by_type)
            logger.info("🎯 OFICIAL - Predicción oficial agregada exitosamente en background")
        except Exception as e:
            logger.error(f"❌ OFICIAL - Error agregando predicción oficial en background: {e}")
            logger.error(f"❌ OFICIAL - Traceback:", exc_info=True)
        
        # Guardar resultados PRIMERO (antes de marcar como completado)
        session['last_prediction'] = {
            'home_team': home_team,
            'away_team': away_team,
            'league': league_name,
            'all_predictions': all_predictions_by_type
        }
        session.modified = True
        session.save()
        
        logger.info(f"✅ SESIÓN GUARDADA - Home: '{home_team}' vs Away: '{away_team}', Liga: {league_name}")
        logger.info(f"📝 DATOS EN SESIÓN - Total de tipos de predicción: {len(all_predictions_by_type)}")
        
        
        # Marcar como completado DESPUÉS de guardar los resultados
        session['prediction_progress'] = {
            'current': total_types,
            'total': total_types,
            'current_type': 'Completado',
            'status': 'completed'
        }
        session.modified = True
        session.save()
        
        logger.info("Predicciones completadas en background")
        
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO EN BACKGROUND: {e}")
        logger.error(f"❌ TRACEBACK COMPLETO:", exc_info=True)
        # Marcar como error
        try:
            session['prediction_progress'] = {
                'current': 0,
                'total': 10,
                'current_type': 'Error',
                'status': 'error'
            }
            session.save()
        except:
            pass


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class PredictionDashboardView(View):
    """Dashboard principal de predicciones"""
    
    def get(self, request):
        # Usar contexto básico sin dependencias de modelos de IA
        context = {
            'leagues': League.objects.all(),
            'recent_predictions': [],
            'available_models': [],
        }
        return render(request, 'ai_predictions/dashboard.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class PredictionFormView(View):
    """Vista para el formulario de predicción"""
    
    def get(self, request):
        form = PredictionForm()
        leagues = League.objects.all()
        
        context = {
            'form': form,
            'leagues': leagues,
        }
        return render(request, 'ai_predictions/prediction_form.html', context)
    
    def post(self, request):
        logger.info("Iniciando procesamiento de predicción...")
        form = PredictionForm(request.POST)
        
        if form.is_valid():
            logger.info("Formulario válido, procesando datos...")
            try:
                home_team = form.cleaned_data['home_team']
                away_team = form.cleaned_data['away_team']
                league = form.cleaned_data['league']
                logger.info(f"📋 FORMULARIO RECIBIDO - Home: '{home_team}' vs Away: '{away_team}', Liga: {league.name}")
                
                # Inicializar progreso en sesión (barra existente) y limpiar anterior
                if 'last_prediction' in request.session:
                    logger.info(f"🧹 LIMPIANDO PREDICCIÓN ANTERIOR: {request.session['last_prediction'].get('home_team')} vs {request.session['last_prediction'].get('away_team')}")
                    del request.session['last_prediction']
                request.session['prediction_progress'] = {
                    'current': 0,
                    'total': 11,
                    'current_type': 'Preparando...',
                    'status': 'running'
                }
                request.session.modified = True
                request.session.save()
                
                request.session['prediction_progress'] = {
                    'current': 0,
                    'total': 11,
                    'current_type': 'Iniciando...',
                    'status': 'processing'
                }
                request.session.modified = True
                request.session.save()
                
                # Procesar predicciones DIRECTAMENTE (sin threading)
                logger.info("🔄 PROCESANDO DIRECTAMENTE - sin threading")
                
                from .simple_models import SimplePredictionService, ModeloHibridoCorners, ModeloHibridoGeneral
                from .league_calibration import league_calibration
                from .enhanced_both_teams_score import enhanced_both_teams_score_model
                
                prediction_types = [
                    'shots_total', 'shots_home', 'shots_away',
                    'shots_on_target_total',
                    'goals_total', 'goals_home', 'goals_away',
                    'corners_total', 'corners_home', 'corners_away',
                    'both_teams_score'
                ]
                
                all_predictions_by_type = {}
                simple_service = SimplePredictionService()
                
                for i, pred_type in enumerate(prediction_types, 1):
                    logger.info(f"🔧 PROCESANDO {i}/{len(prediction_types)} - {pred_type}")
                    # Actualizar progreso visible para la barra
                    try:
                        request.session['prediction_progress'] = {
                            'current': i - 1,
                            'total': len(prediction_types),
                            'current_type': pred_type,
                            'status': 'running'
                        }
                        request.session.modified = True
                        request.session.save()
                    except Exception as e:
                        logger.debug(f"No se pudo actualizar progreso: {e}")
                    
                    try:
                        # MANEJO ESPECIAL PARA REMATES - USAR AMBOS MODELOS
                        if 'shots' in pred_type or 'remates' in pred_type:
                            logger.info(f"🎯 [BACKGROUND] ENTRANDO A MANEJO ESPECIAL DE REMATES (AMBOS MODELOS) para {pred_type}")
                            predictions = []
                            
                            try:
                                # Modelo 1: Shots Prediction Model (original)
                                from .shots_prediction_model import shots_prediction_model
                                logger.info(f"🎯 [BACKGROUND] IMPORTACIÓN EXITOSA de shots_prediction_model para {pred_type}")
                                
                                if pred_type == 'shots_total':
                                    pred1 = shots_prediction_model.predict_shots_total(home_team, away_team, league)
                                elif pred_type == 'shots_home':
                                    pred1 = shots_prediction_model.predict_shots_home(home_team, away_team, league)
                                elif pred_type == 'shots_away':
                                    pred1 = shots_prediction_model.predict_shots_away(home_team, away_team, league)
                                elif pred_type == 'shots_on_target_total':
                                    pred1 = shots_prediction_model.predict_shots_on_target_total(home_team, away_team, league)
                                else:
                                    pred1 = None
                                
                                if pred1:
                                    predictions.append(pred1)
                                    logger.info(f"🎯 [BACKGROUND] MODELO 1 (Shots Prediction) agregado para {pred_type}")
                                
                            except Exception as e:
                                logger.error(f"❌ [BACKGROUND] ERROR EN shots_prediction_model para {pred_type}: {e}")
                            
                            try:
                                # Modelo 2: XG Shots Model (nuevo)
                                from .xg_shots_model import xg_shots_model
                                logger.info(f"🎯 [BACKGROUND] IMPORTACIÓN EXITOSA de xg_shots_model para {pred_type}")
                                
                                if pred_type == 'shots_total':
                                    pred2 = xg_shots_model.predict_shots_total(home_team, away_team, league)
                                elif pred_type == 'shots_home':
                                    pred2 = xg_shots_model.predict_shots_home(home_team, away_team, league)
                                elif pred_type == 'shots_away':
                                    pred2 = xg_shots_model.predict_shots_away(home_team, away_team, league)
                                elif pred_type == 'shots_on_target_total':
                                    pred2 = xg_shots_model.predict_shots_on_target_total(home_team, away_team, league)
                                else:
                                    pred2 = None
                                
                                if pred2:
                                    predictions.append(pred2)
                                    logger.info(f"🎯 [BACKGROUND] MODELO 2 (XG Shots) agregado para {pred_type}")
                                
                            except Exception as e:
                                logger.error(f"❌ [BACKGROUND] ERROR EN xg_shots_model para {pred_type}: {e}")
                            
                            logger.info(f"🎯 [BACKGROUND] TOTAL MODELOS DE REMATES para {pred_type}: {len(predictions)} modelos")
                            logger.info(f"🎯 [BACKGROUND] PREDICCIONES GENERADAS: {predictions}")
                        else:
                            # Obtener predicciones simples para otros mercados
                            predictions = simple_service.get_all_simple_predictions(home_team, away_team, league, pred_type)
                            
                            # Agregar modelo híbrido solo para mercados no-shots
                            if 'corners' in pred_type:
                                hybrid_model = ModeloHibridoCorners()
                                hybrid_prediction = hybrid_model.predecir(home_team, away_team, league, pred_type)
                                predictions.append(hybrid_prediction)
                            else:
                                hybrid_model = ModeloHibridoGeneral()
                                hybrid_prediction = hybrid_model.predecir(home_team, away_team, league, pred_type)
                                predictions.append(hybrid_prediction)
                        
                        # APLICAR CALIBRACIÓN POR LIGA
                        calibrated_predictions = []
                        for pred in predictions:
                            calibrated_value = league_calibration.calibrate_prediction(
                                pred['prediction'], pred_type, league.name
                            )
                            
                            # Crear nueva predicción calibrada
                            calibrated_pred = {
                                'model_name': pred['model_name'],
                                'prediction': calibrated_value,
                                'confidence': pred['confidence'],
                                'probabilities': pred['probabilities'],
                                'total_matches': pred['total_matches']
                            }
                            calibrated_predictions.append(calibrated_pred)
                        
                        # USAR MODELO MEJORADO PARA AMBOS MARCAN
                        if pred_type == 'both_teams_score':
                            # Usar modelo mejorado que no requiere entrenamiento
                            enhanced_prob = enhanced_both_teams_score_model.predict(home_team, away_team, league)
                            
                            # Crear predicción con modelo mejorado
                            enhanced_prediction = {
                                'model_name': "Enhanced Both Teams Score",
                                'prediction': enhanced_prob,
                                'confidence': 0.80,  # Alta confianza para modelo mejorado
                                'probabilities': {'both_score': enhanced_prob},
                                'total_matches': 100  # Modelo robusto con múltiples enfoques
                            }
                            calibrated_predictions.append(enhanced_prediction)
                        
                        # Las predicciones ya están en formato diccionario
                        predictions_dict = calibrated_predictions
                        
                        all_predictions_by_type[pred_type] = predictions_dict
                        logger.info(f"✅ {pred_type}: {len(predictions_dict)} modelos generados (calibrados)")
                        
                    except Exception as e:
                        logger.error(f"❌ ERROR EN {pred_type}: {e}")
                        all_predictions_by_type[pred_type] = []
                
                # AGREGAR PREDICCIÓN OFICIAL (después de todos los otros modelos)
                logger.info("🎯 OFICIAL - Iniciando cálculo de predicción oficial")
                try:
                    from .official_prediction_model import official_prediction_model
                    all_predictions_by_type = official_prediction_model.add_to_predictions(all_predictions_by_type)
                    logger.info("🎯 OFICIAL - Predicción oficial agregada exitosamente")
                except Exception as e:
                    logger.error(f"❌ OFICIAL - Error agregando predicción oficial: {e}")
                    logger.error(f"❌ OFICIAL - Traceback:", exc_info=True)
                
                # Guardar resultados persistidos para evitar pérdida en sesiones multi-worker
                prediction_payload = convert_numpy_to_native(all_predictions_by_type)
                saved_prediction = SavedPrediction.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    all_predictions=prediction_payload,
                    metadata={
                        'generated_at': timezone.now().isoformat(),
                        'prediction_types': prediction_types,
                    }
                )

                # Guardar resultados en sesión (compatibilidad)
                request.session['last_prediction'] = {
                    'home_team': home_team,
                    'away_team': away_team,
                    'league': league.name,
                    'all_predictions': prediction_payload,
                    'saved_prediction_id': str(saved_prediction.id),
                }
                request.session.modified = True
                request.session.save()
                # Marcar progreso como completado
                try:
                    request.session['prediction_progress'] = {
                        'current': len(prediction_types),
                        'total': len(prediction_types),
                        'current_type': 'Completado',
                        'status': 'completed'
                    }
                    request.session.modified = True
                    request.session.save()
                except Exception as e:
                    logger.debug(f"No se pudo marcar progreso completado: {e}")
                
                logger.info(f"✅ PREDICCIONES COMPLETADAS - Home: '{home_team}' vs Away: '{away_team}', Liga: {league.name}")
                logger.info(f"📝 DATOS GUARDADOS - Total de tipos: {len(all_predictions_by_type)}")
                
                # Redirigir directamente a resultados persistidos
                return redirect('ai_predictions:prediction_result_with_id', prediction_id=saved_prediction.id)
                
            except Exception as e:
                logger.error(f"Error en predicción: {e}")
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)
        else:
            logger.error(f"Formulario inválido: {form.errors}")
            return JsonResponse({
                'status': 'error',
                'message': 'Formulario inválido',
                'errors': form.errors
            }, status=400)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class PredictionResultView(View):
    """Vista para mostrar resultados de predicción"""
    
    def get(self, request, prediction_id=None):
        logger.info("🎯 INICIANDO PredictionResultView.get()")
        logger.info(f"🎯 REQUEST PATH: {request.path}")
        logger.info(f"🎯 REQUEST METHOD: {request.method}")
        logger.info(f"🎯 SESSION KEY: {request.session.session_key}")

        prediction_payload = None

        if prediction_id:
            saved_prediction = get_object_or_404(SavedPrediction, id=prediction_id)
            if saved_prediction.user and saved_prediction.user != request.user and not request.user.is_staff:
                messages.error(request, "No tienes permiso para ver esta predicción.")
                return redirect('ai_predictions:prediction_form')

            prediction_payload = {
                'home_team': saved_prediction.home_team,
                'away_team': saved_prediction.away_team,
                'league': saved_prediction.league.name,
                'all_predictions': saved_prediction.all_predictions,
                'saved_prediction_id': str(saved_prediction.id),
                'created_at': saved_prediction.created_at.isoformat(),
            }
            logger.info(f"🎯 PREDICCIÓN PERSISTIDA OBTENIDA: {saved_prediction.id}")
        else:
            prediction_payload = request.session.get('last_prediction')
            logger.info(f"🎯 SESIÓN OBTENIDA: {prediction_payload is not None}")

        if not prediction_payload:
            logger.info("🎯 REDIRIGIENDO: No hay predicciones en sesión")
            messages.info(request, "No hay predicciones recientes.")
            return redirect('ai_predictions:prediction_form')

        # Log para verificar qué equipos se están mostrando
        logger.info(f"📊 MOSTRANDO RESULTADOS - Home: '{prediction_payload.get('home_team')}' vs Away: '{prediction_payload.get('away_team')}', Liga: {prediction_payload.get('league')}")
        
        # Log detallado de la estructura de la predicción
        logger.info(f"🔍 ESTRUCTURA DE PREDICCIÓN: {list(prediction_payload.keys())}")
        if 'all_predictions' in prediction_payload:
            logger.info(f"🔍 TIPOS DE PREDICCIÓN: {list(prediction_payload['all_predictions'].keys())}")
            logger.info(f"🔍 TOTAL TIPOS: {len(prediction_payload['all_predictions'])}")
        else:
            logger.error("❌ ERROR: 'all_predictions' no existe en la sesión")
        
        # Verificar que la predicción esté completa
        if 'all_predictions' not in prediction_payload or not prediction_payload['all_predictions']:
            logger.error("❌ ERROR: Predicción incompleta - faltan datos")
            logger.error(f"❌ ESTRUCTURA COMPLETA: {prediction_payload}")
            messages.error(request, "Error: La predicción no se completó correctamente. Por favor, intenta nuevamente.")
            return redirect('ai_predictions:prediction_form')
        
        # Obtener todos los nombres de modelos únicos
        model_names = set()
        total_models = 0
        if 'all_predictions' in prediction_payload:
            for pred_type, predictions in prediction_payload['all_predictions'].items():
                total_models += len(predictions)
                pred_model_names = [pred['model_name'] for pred in predictions]
                logger.info(f"Tipo {pred_type}: {len(predictions)} modelos - {pred_model_names}")
                for pred in predictions:
                    model_names.add(pred['model_name'])
        
        model_names = sorted(list(model_names))
        
        # Log para debugging
        logger.info(f"Modelos únicos encontrados: {model_names}")
        logger.info(f"Total de modelos generados: {total_models}")
        logger.info(f"Tipos de predicción: {list(prediction_payload.get('all_predictions', {}).keys())}")
        
        # Verificación de que tenemos 3 modelos únicos
        if len(model_names) < 3:
            logger.warning(f"Solo se encontraron {len(model_names)} modelos únicos, esperados 3")
            logger.warning(f"Modelos encontrados: {model_names}")
        else:
            logger.info(f"[OK] Se encontraron {len(model_names)} modelos únicos correctamente")
        
        context = {
            'prediction': prediction_payload,
            'model_names': model_names
        }
        return render(request, 'ai_predictions/prediction_result_new.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class TrainingView(View):
    """Vista para entrenar modelos"""
    
    def get(self, request):
        leagues = League.objects.all()
        
        # Usar lista vacía en lugar de consulta a modelo inexistente
        context = {
            'leagues': leagues,
            'models': [],  # Lista vacía para evitar errores de DB
        }
        return render(request, 'ai_predictions/training.html', context)
    
    def post(self, request):
        try:
            league_id = request.POST.get('league_id')
            prediction_type = request.POST.get('prediction_type', 'shots_total')
            
            league = League.objects.get(id=league_id)
            trainer = ModelTrainer()
            
            # Entrenar modelo optimizado
            train_result = trainer.train_optimized_model(league, prediction_type)
            
            if 'error' in train_result:
                messages.error(request, f"Error entrenando modelo: {train_result['error']}")
            else:
                messages.success(request, 
                    f"Modelo {train_result['model_name']} entrenado exitosamente para {league.name}. "
                    f"Score: {train_result['score']:.3f}, "
                    f"Muestras: {train_result['samples_count']}, "
                    f"Características: {train_result['features_count']}"
                )
            
        except Exception as e:
            logger.error(f"Error entrenando modelo: {e}")
            messages.error(request, f"Error entrenando modelo: {str(e)}")
        
        return redirect('ai_predictions:training')


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class GetTeamsView(View):
    """API para obtener equipos de una liga"""
    
    def get(self, request, league_id):
        try:
            league = League.objects.get(id=league_id)
            
            # Obtener equipos únicos de la liga
            home_teams = Match.objects.filter(league=league).values_list('home_team', flat=True).distinct()
            away_teams = Match.objects.filter(league=league).values_list('away_team', flat=True).distinct()
            
            all_teams = sorted(list(set(list(home_teams) + list(away_teams))))
            
            return JsonResponse({
                'teams': all_teams
            })
            
        except League.DoesNotExist:
            return JsonResponse({'error': 'Liga no encontrada'}, status=404)
        except Exception as e:
            logger.error(f"Error obteniendo equipos: {e}")
            return JsonResponse({'error': str(e)}, status=500)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class PredictionProgressView(View):
    """API para obtener el progreso de la predicción"""
    
    def get(self, request):
        try:
            progress = request.session.get('prediction_progress', {
                'current': 0,
                'total': 11,
                'current_type': 'Iniciando...',
                'status': 'idle'
            })
            
            return JsonResponse(progress)
            
        except Exception as e:
            logger.error(f"Error obteniendo progreso: {e}")
            return JsonResponse({'error': str(e)}, status=500)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class PredictionHistoryView(View):
    """Vista para historial de predicciones"""
    
    def get(self, request):
        # Usar lista vacía para evitar errores de DB
        predictions = []
        
        # Filtros
        league_filter = request.GET.get('league')
        
        # Paginación (con lista vacía)
        paginator = Paginator(predictions, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'leagues': League.objects.all(),
            'selected_league': league_filter,
        }
        return render(request, 'ai_predictions/prediction_history.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class ModelPerformanceView(View):
    """Vista para rendimiento de modelos"""
    
    def get(self, request):
        # Usar lista vacía para evitar errores de DB
        models = []
        
        context = {
            'models': models,
        }
        return render(request, 'ai_predictions/model_performance.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class QuickPredictionView(View):
    """Vista para predicción rápida con AJAX"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            home_team = data.get('home_team')
            away_team = data.get('away_team')
            league_id = data.get('league_id')
            prediction_type = data.get('prediction_type', 'shots_total')
            
            league = League.objects.get(id=league_id)
            
            advanced_service = AdvancedStatisticalModels()
            all_predictions = advanced_service.get_all_advanced_predictions(home_team, away_team, league, prediction_type)
            
            multi_service = MultiModelPredictionService()
            backtest_results = multi_service.backtest_models(league, prediction_type)
            
            return JsonResponse({
                'predictions': all_predictions,
                'backtest_results': backtest_results
            })
            
        except Exception as e:
            logger.error(f"Error en predicción rápida: {e}")
            return JsonResponse({'error': str(e)}, status=500)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class TestPredictionsView(View):
    """Vista de prueba para verificar predicciones avanzadas"""
    
    def get(self, request):
        try:
            league = League.objects.first()
            if not league:
                return JsonResponse({'error': 'No hay ligas disponibles'})
            
            advanced_service = AdvancedStatisticalModels()
            predictions = advanced_service.get_all_advanced_predictions('Dortmund', 'Hannover', league, 'shots_total')
            
            return JsonResponse({
                'success': True,
                'predictions': predictions,
                'count': len(predictions)
            })
            
        except Exception as e:
            logger.error(f"Error en vista de prueba: {e}")
            return JsonResponse({'error': str(e)})


# @method_decorator(login_required, name='dispatch')
@method_decorator(login_required, name='dispatch')
class LeagueHistoricalDataView(View):
    """Vista para obtener datos históricos de una liga para gráficas"""
    
    def get(self, request, league_id):
        try:
            league = League.objects.get(id=league_id)
            
            # Obtener partidos de la liga de los últimos 6 meses
            six_months_ago = datetime.now() - timedelta(days=180)
            matches = Match.objects.filter(
                league=league,
                date__gte=six_months_ago
            ).exclude(
                Q(hs__isnull=True) | Q(as_field__isnull=True) | 
                Q(fthg__isnull=True) | Q(ftag__isnull=True) |
                Q(hc__isnull=True) | Q(ac__isnull=True)
            ).order_by('date')
            
            # Agrupar datos por fecha
            daily_data = defaultdict(lambda: {
                'date': None,
                'shots_total': 0,
                'goals_total': 0,
                'corners_total': 0,
                'matches_count': 0
            })
            
            for match in matches:
                date_key = match.date.strftime('%Y-%m-%d')
                
                # Calcular totales del partido
                shots_total = (match.hs or 0) + (match.as_field or 0)
                goals_total = (match.fthg or 0) + (match.ftag or 0)
                corners_total = (match.hc or 0) + (match.ac or 0)
                
                daily_data[date_key]['date'] = date_key
                daily_data[date_key]['shots_total'] += shots_total
                daily_data[date_key]['goals_total'] += goals_total
                daily_data[date_key]['corners_total'] += corners_total
                daily_data[date_key]['matches_count'] += 1
            
            # Convertir a lista y ordenar por fecha
            chart_data = []
            for date_key in sorted(daily_data.keys()):
                data = daily_data[date_key]
                chart_data.append({
                    'date': data['date'],
                    'shots_total': data['shots_total'],
                    'goals_total': data['goals_total'],
                    'corners_total': data['corners_total'],
                    'matches_count': data['matches_count']
                })
            
            # Limitar a los últimos 60 días con datos
            chart_data = chart_data[-60:] if len(chart_data) > 60 else chart_data
            
            return JsonResponse({
                'success': True,
                'league_name': league.name,
                'data': chart_data,
                'total_days': len(chart_data),
                'date_range': {
                    'start': chart_data[0]['date'] if chart_data else None,
                    'end': chart_data[-1]['date'] if chart_data else None
                }
            })
            
        except League.DoesNotExist:
            return JsonResponse({'error': 'Liga no encontrada'}, status=404)
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {e}")
            return JsonResponse({'error': str(e)}, status=500)
