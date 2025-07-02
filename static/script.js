// Variables globales
let currentTab = 'qobuz';
let searchResults = [];
let isSearching = false;

// Inicialización cuando carga la página
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeSearch();
    initializeModal();
    checkTokenStatus();
});

// Inicializar tabs
function initializeTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const source = this.getAttribute('data-source');
            const oldTab = document.querySelector('.tab-btn.active');
            
            // Actualizar tabs activos
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Animar cambio de tab con Anime.js
            if (window.animationManager) {
                window.animationManager.animateTabChange(this, oldTab);
            }
            
            // Actualizar hints
            const hints = document.querySelectorAll('[class*="hint-"]');
            hints.forEach(hint => hint.classList.add('hidden'));
            
            const activeHint = document.querySelector(`.hint-${source}`);
            if (activeHint) {
                activeHint.classList.remove('hidden');
            }
            
            currentTab = source;
            clearResults();
        });
    });
}

// Inicializar búsqueda
function initializeSearch() {
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearBtn');
    
    searchBtn.addEventListener('click', performSearch);
    
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    // Añadir evento para detectar tipo de búsqueda mientras escribe
    searchInput.addEventListener('input', function(e) {
        updateSearchHint(e.target.value);
        toggleClearButton(e.target.value);
    });
    
    // Funcionalidad del botón limpiar
    clearBtn.addEventListener('click', function() {
        searchInput.value = '';
        searchInput.focus();
        toggleClearButton('');
        updateSearchHint('');
        clearResults();
    });
}

// Mostrar/ocultar botón de limpiar
function toggleClearButton(value) {
    const clearBtn = document.getElementById('clearBtn');
    if (value.trim().length > 0) {
        clearBtn.classList.remove('hidden');
        clearBtn.classList.add('show');
    } else {
        clearBtn.classList.add('hidden');
        clearBtn.classList.remove('show');
    }
}

// Inicializar modal
function initializeModal() {
    const modal = document.getElementById('downloadModal');
    const closeBtn = document.getElementById('modalClose');
    
    closeBtn.addEventListener('click', function() {
        if (window.animationManager) {
            window.animationManager.animateModal(false);
        } else {
            modal.classList.add('hidden');
        }
    });
    
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            if (window.animationManager) {
                window.animationManager.animateModal(false);
            } else {
                modal.classList.add('hidden');
            }
        }
    });
}

// Detectar tipo de búsqueda y mostrar indicador
function detectSearchType(query) {
    const words = query.split();
    const isLikelyLyrics = words.length >= 4 && !query.toLowerCase().includes('album') && 
                          !query.toLowerCase().includes('artist') && 
                          !query.toLowerCase().includes('song');
    
    return {
        isLyrics: isLikelyLyrics,
        wordCount: words.length
    };
}

function updateSearchHint(query) {
    const searchType = detectSearchType(query);
    const hintElement = document.querySelector('.hint-qobuz');
    
    if (currentTab === 'qobuz' && hintElement) {
        if (searchType.isLyrics) {
            hintElement.innerHTML = '🎤 Búsqueda inteligente - Ignora tildes, comas, puntuación y mayúsculas';
            hintElement.style.color = '#7FB069';
        } else {
            hintElement.innerHTML = '💡 Busca por título, artista, álbum o frase de letra (ignora tildes, puntuación y mayúsculas)';
            hintElement.style.color = '';
        }
    }
}

// Realizar búsqueda
async function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const query = searchInput.value.trim();
    
    console.log('Performing search:', query, 'Tab:', currentTab);
    
    if (!query) {
        showError('Por favor ingresa un término de búsqueda o enlace');
        return;
    }
    
    if (isSearching) {
        return;
    }
    
    setSearching(true);
    clearResults();
    
    // Mostrar mensaje personalizado basado en el tipo de búsqueda
    const searchType = detectSearchType(query);
    const loadingMessage = searchType.isLyrics ? 
        'Buscando por letra en Genius (puede tardar unos segundos)...' : 
        'Buscando...';
    
    showLoading(loadingMessage);
    
    try {
        console.log('Sending request to /api/search');
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                source: currentTab
            })
        });
        
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success) {
            searchResults = data.results;
            displayResults(searchResults);
        } else {
            showError(data.error || 'Error en la búsqueda');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error de conexión. Verifica que el servidor esté funcionando.');
    } finally {
        setSearching(false);
        hideLoading();
    }
}

// Mostrar resultados
function displayResults(results) {
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsHeader = document.getElementById('resultsHeader');
    const resultsCount = document.getElementById('resultsCount');
    
    if (!results || results.length === 0) {
        resultsContainer.innerHTML = '<div class="no-results">No se encontraron resultados</div>';
        resultsHeader.classList.add('hidden');
        return;
    }
    
    // Contar resultados por tipo
    const geniusResults = results.filter(r => r.genius_match);
    const lyricsResults = results.filter(r => r.found_by_lyrics);
    const normalResults = results.filter(r => !r.found_by_lyrics);
    
    // Mostrar header con contador detallado
    resultsHeader.classList.remove('hidden');
    let countText = `${results.length} resultado${results.length !== 1 ? 's' : ''}`;
    
    if (geniusResults.length > 0) {
        countText += ` (${geniusResults.length} de Genius con letra confirmada)`;
    } else if (lyricsResults.length > 0) {
        countText += ` (${lyricsResults.length} por letra)`;
    }
    
    resultsCount.textContent = countText;
    
    const resultsHTML = results.map((result, index) => {
        const coverImage = result.cover ? 
            `<img src="${escapeHtml(result.cover)}" alt="Cover" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">
             <div class="result-cover-placeholder" style="display: none;">🎵</div>` :
            `<div class="result-cover-placeholder">🎵</div>`;
            
        // Detectar si fue encontrado por búsqueda de letra
        let lyricsIndicator = '';
        if (result.found_by_lyrics) {
            if (result.genius_match) {
                lyricsIndicator = '<span class="lyrics-indicator genius" title="Encontrado en Genius - Letra confirmada">🎤✨</span>';
            } else {
                lyricsIndicator = '<span class="lyrics-indicator" title="Encontrado por letra">🎤</span>';
            }
        }
            
        return `
            <div class="result-item" data-index="${index}">
                <div class="result-cover">
                    ${coverImage}
                </div>
                <div class="result-info">
                    <div class="result-title">
                        ${escapeHtml(result.title)}
                        ${lyricsIndicator}
                    </div>
                    <div class="result-artist">${escapeHtml(result.artist)}</div>
                    ${result.album ? `<div class="result-album">${escapeHtml(result.album)}</div>` : ''}
                    ${result.duration ? `<div class="result-duration">${formatDuration(result.duration)}</div>` : ''}
                </div>
                <button class="download-btn" onclick="openDownloadModal(${index})">
                    <span class="download-icon">⬇</span>
                    Descargar
                </button>
            </div>
        `;
    }).join('');
    
    resultsContainer.innerHTML = resultsHTML;
    
    // Animar resultados con Anime.js
    if (window.animationManager) {
        window.animationManager.showNewResults();
    }
}

// Abrir modal de descarga
function openDownloadModal(resultIndex) {
    const result = searchResults[resultIndex];
    if (!result) return;
    
    const modal = document.getElementById('downloadModal');
    const downloadTitle = document.getElementById('downloadTitle');
    const downloadArtist = document.getElementById('downloadArtist');
    const downloadCover = document.getElementById('downloadCover');
    const downloadQuality = document.getElementById('downloadQuality');
    const qualitySelect = document.getElementById('qualitySelect');
    
    // Mostrar información de la canción
    downloadTitle.textContent = result.title;
    downloadArtist.textContent = result.artist;
    
    // Mostrar cover si está disponible
    if (result.cover) {
        downloadCover.src = result.cover;
        downloadCover.style.display = 'block';
    } else {
        downloadCover.style.display = 'none';
    }
    
    // Mostrar calidad seleccionada
    const selectedQuality = qualitySelect.options[qualitySelect.selectedIndex].text;
    downloadQuality.textContent = `Calidad: ${selectedQuality}`;
    
    // Configurar modal para descarga
    modal.dataset.resultIndex = resultIndex;
    
    // Mostrar modal con animación
    if (window.animationManager) {
        window.animationManager.animateModal(true);
    } else {
        modal.classList.remove('hidden');
    }
    
    // Iniciar descarga automáticamente
    setTimeout(() => downloadSong(result), 500);
}

// Descargar canción
async function downloadSong(result) {
    const qualitySelect = document.getElementById('qualitySelect');
    const quality = qualitySelect.value;
    const progressText = document.getElementById('progressText');
    
    progressText.textContent = 'Obteniendo enlace de descarga...';
    if (window.animationManager) {
        window.animationManager.animateProgress(20);
    } else {
        document.getElementById('progressFill').style.width = '20%';
    }
    
    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                track_id: result.id,
                quality: quality
            })
        });
        
        const data = await response.json();
        
        if (data.download_url) {
            progressText.textContent = 'Iniciando descarga...';
            if (window.animationManager) {
                window.animationManager.animateProgress(60);
            } else {
                document.getElementById('progressFill').style.width = '60%';
            }
            
            // Crear nombre de archivo
            const ext = quality === '5' ? '.mp3' : '.flac';
            const filename = `${result.artist} - ${result.title}${ext}`;
            
            // Crear enlace de descarga
            const downloadUrl = `/api/proxy-download?url=${encodeURIComponent(data.download_url)}&filename=${encodeURIComponent(filename)}&track_id=${encodeURIComponent(result.id)}`;
            
            progressText.textContent = 'Descarga completada';
            if (window.animationManager) {
                window.animationManager.animateProgress(100);
            } else {
                document.getElementById('progressFill').style.width = '100%';
            }
            
            // Crear elemento a temporal para descargar
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showSuccess('Descarga iniciada correctamente');
            
            // Cerrar modal después de un momento
            setTimeout(() => {
                if (window.animationManager) {
                    window.animationManager.animateModal(false);
                } else {
                    document.getElementById('downloadModal').classList.add('hidden');
                }
            }, 2000);
        } else {
            progressText.textContent = 'Error en la descarga';
            showError(data.error || 'Error obteniendo enlace de descarga');
        }
    } catch (error) {
        console.error('Error:', error);
        progressText.textContent = 'Error de conexión';
        showError('Error de conexión durante la descarga');
    }
}

// Verificar estado del token
async function checkTokenStatus() {
    const tokenStatus = document.getElementById('tokenStatus');
    const tokenText = tokenStatus.querySelector('.token-text');
    const tokenIcon = tokenStatus.querySelector('.token-icon');
    
    try {
        const response = await fetch('/api/token-info');
        const data = await response.json();
        
        if (data.success && data.token_info) {
            const info = data.token_info;
            
            if (info.token_valido) {
                // Verificar información de suscripción primero
                if (info.suscripcion && info.suscripcion.dias_restantes !== undefined) {
                    const dias = info.suscripcion.dias_restantes;
                    const estado = info.suscripcion.estado_detallado;
                    
                    if (info.suscripcion.expirado || dias < 0) {
                        tokenStatus.className = 'token-status expired';
                        tokenIcon.textContent = '❌';
                        tokenText.textContent = `Suscripción expirada (hace ${Math.abs(dias)} días)`;
                    } else if (dias <= 7) {
                        tokenStatus.className = 'token-status warning';
                        tokenIcon.textContent = '⚠️';
                        tokenText.textContent = `Suscripción expira en ${dias} días`;
                    } else if (dias <= 30) {
                        tokenStatus.className = 'token-status warning';
                        tokenIcon.textContent = '⚡';
                        tokenText.textContent = `Suscripción expira en ${dias} días`;
                    } else {
                        tokenStatus.className = 'token-status valid';
                        tokenIcon.textContent = '✅';
                        tokenText.textContent = `Suscripción activa (${dias} días restantes)`;
                    }
                } else {
                    // Token válido pero sin información de suscripción
                    tokenStatus.className = 'token-status valid';
                    tokenIcon.textContent = '✅';
                    if (info.usuario && info.usuario.email !== 'No disponible') {
                        tokenText.textContent = `Token válido - ${info.usuario.email}`;
                    } else {
                        tokenText.textContent = 'Token válido';
                    }
                }
                
                // Crear tooltip con información detallada
                let tooltipText = `Tipo: ${info.tipo}`;
                if (info.usuario) {
                    tooltipText += `\nUsuario: ${info.usuario.email}`;
                    if (info.usuario.nombre !== 'No disponible') {
                        tooltipText += `\nNombre: ${info.usuario.nombre} ${info.usuario.apellido || ''}`;
                    }
                    tooltipText += `\nPaís: ${info.usuario.pais}`;
                }
                if (info.suscripcion) {
                    tooltipText += `\nSuscripción: ${info.suscripcion.tipo}`;
                    if (info.suscripcion.fecha_expiracion_legible) {
                        tooltipText += `\nExpira: ${info.suscripcion.fecha_expiracion_legible}`;
                    }
                    tooltipText += `\nRenovación automática: ${info.suscripcion.renovacion_automatica ? 'Sí' : 'No'}`;
                }
                if (info.calidad) {
                    tooltipText += `\nCalidad máxima: ${info.calidad.calidad_maxima}`;
                    tooltipText += `\nHi-Res: ${info.calidad.hires_disponible ? 'Sí' : 'No'}`;
                }
                tokenStatus.title = tooltipText;
                
            } else {
                // Token inválido
                tokenStatus.className = 'token-status expired';
                tokenIcon.textContent = '❌';
                tokenText.textContent = 'Token inválido o expirado';
                tokenStatus.title = info.error_api || info.error || 'Error al validar token';
            }
        } else {
            throw new Error(data.error || 'Error al verificar token');
        }
    } catch (error) {
        console.error('Error verificando token:', error);
        tokenStatus.className = 'token-status warning';
        tokenIcon.textContent = '⚠️';
        tokenText.textContent = 'Error verificando token';
        tokenStatus.title = 'No se pudo verificar el estado del token';
    }
}

// Agregar evento click para mostrar información detallada del token
document.addEventListener('DOMContentLoaded', function() {
    const tokenStatus = document.getElementById('tokenStatus');
    if (tokenStatus) {
        tokenStatus.addEventListener('click', function() {
            showTokenDetails();
        });
    }
});

async function showTokenDetails() {
    try {
        const response = await fetch('/api/token-info');
        const data = await response.json();
        
        if (data.success && data.token_info) {
            const info = data.token_info;
            let message = `=== INFORMACIÓN DEL TOKEN DE QOBUZ ===\n\n`;
            
            if (info.token_valido) {
                message += `✅ Token válido\n`;
                message += `Tipo: ${info.tipo}\n\n`;
                
                // Información del usuario
                if (info.usuario) {
                    message += `👤 USUARIO:\n`;
                    message += `  Email: ${info.usuario.email}\n`;
                    if (info.usuario.nombre !== 'No disponible') {
                        message += `  Nombre: ${info.usuario.nombre} ${info.usuario.apellido || ''}\n`;
                    }
                    message += `  País: ${info.usuario.pais}\n`;
                    message += `  ID: ${info.usuario.id}\n\n`;
                }
                
                // Información de suscripción
                if (info.suscripcion) {
                    message += `💳 SUSCRIPCIÓN:\n`;
                    message += `  Tipo: ${info.suscripcion.tipo}\n`;
                    message += `  Estado: ${info.suscripcion.estado}\n`;
                    
                    if (info.suscripcion.fecha_expiracion_legible) {
                        message += `  📅 Expira: ${info.suscripcion.fecha_expiracion_legible}\n`;
                        const dias = info.suscripcion.dias_restantes;
                        if (dias < 0) {
                            message += `  ❌ EXPIRADA (hace ${Math.abs(dias)} días)\n`;
                        } else if (dias <= 7) {
                            message += `  ⚠️ EXPIRA EN ${dias} DÍAS\n`;
                        } else {
                            message += `  ✅ ${dias} días restantes\n`;
                        }
                    } else {
                        message += `  📅 Fecha de expiración: No disponible\n`;
                    }
                    
                    message += `  🔄 Renovación automática: ${info.suscripcion.renovacion_automatica ? 'Sí' : 'No'}\n\n`;
                }
                
                // Información de calidad
                if (info.calidad) {
                    message += `🎵 CALIDAD DISPONIBLE:\n`;
                    message += `  MP3: ${info.calidad.nivel}\n`;
                    message += `  FLAC: ${info.calidad.calidad_maxima}\n`;
                    message += `  Hi-Res: ${info.calidad.hires_disponible ? 'Sí' : 'No'}\n`;
                }
                
            } else {
                message += `❌ Token inválido o expirado\n`;
                if (info.error_api) {
                    message += `Error de API: ${info.error_api}\n`;
                }
                if (info.error) {
                    message += `Error: ${info.error}\n`;
                }
                if (info.nota) {
                    message += `Nota: ${info.nota}\n`;
                }
            }
            
            alert(message);
        } else {
            alert('Error al obtener información del token: ' + (data.error || 'Error desconocido'));
        }
    } catch (error) {
        console.error('Error obteniendo información del token:', error);
        alert('Error al obtener información del token');
    }
}

// Funciones de utilidad
function setSearching(searching) {
    isSearching = searching;
    const searchBtn = document.getElementById('searchBtn');
    searchBtn.disabled = searching;
    if (searching) {
        searchBtn.innerHTML = '<span class="search-icon">⏳</span>';
    } else {
        searchBtn.innerHTML = '<span class="search-icon">🔍</span>';
    }
}

function clearResults() {
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsHeader = document.getElementById('resultsHeader');
    resultsContainer.innerHTML = '';
    resultsHeader.classList.add('hidden');
    searchResults = [];
}

function showLoading(message) {
    const loading = document.getElementById('loading');
    const loadingText = loading.querySelector('p');
    loadingText.textContent = message;
    loading.classList.remove('hidden');
}

function hideLoading() {
    const loading = document.getElementById('loading');
    loading.classList.add('hidden');
}

function showError(message) {
    const errorElement = document.getElementById('errorMessage');
    const errorText = errorElement.querySelector('.error-text');
    errorText.textContent = message;
    errorElement.classList.remove('hidden');
    
    // Auto-hide después de 5 segundos
    setTimeout(() => {
        errorElement.classList.add('hidden');
    }, 5000);
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showNotification(message, type) {
    // Remover notificación anterior si existe
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Crear nueva notificación
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Mostrar notificación
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
    
    // Remover después de 5 segundos
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}
