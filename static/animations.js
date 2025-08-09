/**
 * Animaciones con Anime.js para Music Downloader
 */

// Configuración global de animaciones
const ANIMATION_CONFIG = {
    duration: 300,
    easing: 'easeOutCubic',
    delay: anime.stagger(40),
};

// Clase principal para manejar animaciones
class AnimationManager {
    constructor() {
        this.init();
    }

    init() {
        // Animaciones de entrada cuando se carga la página
        this.animatePageEntry();
        
        // Configurar animaciones de interacción
        this.setupInteractionAnimations();

        // Manejar cambios de orientación y resize
        this.handleResize();
    }

    // Detectar si es dispositivo móvil
    isMobile() {
        return window.innerWidth <= 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    // Ajustar configuración para móviles
    getMobileConfig() {
        if (this.isMobile()) {
            return {
                duration: 250,
                easing: 'easeOutCubic',
                delay: anime.stagger(25),
            };
        }
        return ANIMATION_CONFIG;
    }

    // Animaciones de entrada de la página
    animatePageEntry() {
        const config = this.getMobileConfig();
        
        // Animar logo con efecto de escritura
        anime.timeline({
            easing: 'easeOutExpo',
            duration: config.duration + 80
        })
        .add({
            targets: '.logo h1',
            opacity: [0, 1],
            scale: [0.8, 1],
            translateY: [-30, 0],
            duration: config.duration + 20,
        })
        .add({
            targets: '.logo p',
            opacity: [0, 1],
            translateY: [20, 0],
            duration: config.duration - 30,
        }, this.isMobile() ? '-=120' : '-=170')
        .add({
            targets: '.search-section',
            opacity: [0, 1],
            translateY: [40, 0],
            duration: config.duration,
        }, this.isMobile() ? '-=90' : '-=120')
        .add({
            targets: '.quality-section',
            opacity: [0, 1],
            translateY: [30, 0],
            duration: config.duration - 20,
        }, this.isMobile() ? '-=70' : '-=90');

        // Animar tabs con efecto de onda
        anime({
            targets: '.tab-btn',
            opacity: [0, 1],
            translateY: [-20, 0],
            scale: [0.9, 1],
            duration: config.duration + 20,
            delay: anime.stagger(this.isMobile() ? 40 : 60, {start: this.isMobile() ? 250 : 450}),
            easing: 'easeOutBack'
        });
    }

    // Animar resultados de búsqueda
    animateSearchResults(results) {
        // Primero ocultar resultados existentes
        anime({
            targets: '.result-item',
            opacity: 0,
            translateY: -20,
            scale: 0.9,
            duration: 180,
            easing: 'easeInQuart',
            complete: () => {
                // Luego mostrar nuevos resultados
                this.showNewResults();
            }
        });
    }

    showNewResults() {
        const config = this.getMobileConfig();
        
        // Animar entrada de nuevos resultados
        anime({
            targets: '.result-item',
            opacity: [0, 1],
            translateY: [30, 0],
            scale: [0.9, 1],
            rotateX: this.isMobile() ? [0, 0] : [90, 0], // Menos rotación en móvil
            duration: config.duration + 50,
            delay: anime.stagger(this.isMobile() ? 30 : 40),
            easing: 'easeOutBack'
        });

        // Animar covers con efecto de revelado
        anime({
            targets: '.result-cover img',
            opacity: [0, 1],
            scale: [1.2, 1],
            duration: config.duration + 80,
            delay: anime.stagger(this.isMobile() ? 35 : 50, {start: this.isMobile() ? 70 : 90}),
            easing: 'easeOutCubic'
        });
    }

    // Configurar animaciones de hover e interacción
    setupInteractionAnimations() {
        // Animaciones de hover para tarjetas de resultados
        this.setupResultCardHovers();
        
        // Animaciones para botones
        this.setupButtonAnimations();
        
        // Animaciones para inputs
        this.setupInputAnimations();
    }

    setupResultCardHovers() {
        document.addEventListener('mouseenter', (e) => {
            if (e.target.closest('.result-item')) {
                const card = e.target.closest('.result-item');
                anime({
                    targets: card,
                    translateY: -8,
                    scale: 1.02,
                    boxShadow: '0 12px 30px rgba(0, 0, 0, 0.2)',
                    duration: 250,
                    easing: 'easeOutCubic'
                });

                // Animar cover con rotación sutil
                const cover = card.querySelector('.result-cover');
                if (cover) {
                    anime({
                        targets: cover,
                        rotate: '2deg',
                        scale: 1.05,
                        duration: 250,
                        easing: 'easeOutCubic'
                    });
                }
            }
        }, true);

        document.addEventListener('mouseleave', (e) => {
            if (e.target.closest('.result-item')) {
                const card = e.target.closest('.result-item');
                anime({
                    targets: card,
                    translateY: 0,
                    scale: 1,
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
                    duration: 250,
                    easing: 'easeOutCubic'
                });

                const cover = card.querySelector('.result-cover');
                if (cover) {
                    anime({
                        targets: cover,
                        rotate: '0deg',
                        scale: 1,
                        duration: 250,
                        easing: 'easeOutCubic'
                    });
                }
            }
        }, true);
    }

    setupButtonAnimations() {
        // Animación para botones de descarga
        document.addEventListener('mouseenter', (e) => {
            if (e.target.classList.contains('download-btn') && !this.isMobile()) {
                anime({
                    targets: e.target,
                    scale: 1.05,
                    translateY: -2,
                    duration: 120,
                    easing: 'easeOutCubic'
                });
            }
        }, true);

        document.addEventListener('mouseleave', (e) => {
            if (e.target.classList.contains('download-btn') && !this.isMobile()) {
                anime({
                    targets: e.target,
                    scale: 1,
                    translateY: 0,
                    duration: 120,
                    easing: 'easeOutCubic'
                });
            }
        }, true);

        // Animación de click para botones
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('download-btn') || e.target.classList.contains('search-btn')) {
                const scaleFactor = this.isMobile() ? 0.92 : 0.95;
                anime({
                    targets: e.target,
                    scale: [1, scaleFactor, 1],
                    duration: this.isMobile() ? 140 : 120,
                    easing: 'easeOutCubic'
                });

                // Efecto de ondas solo en desktop
                if (!this.isMobile()) {
                    this.createRippleEffect(e.target, e);
                }
            }
        }, true);

        // Animación para tabs
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('tab-btn')) {
                // Animar tab seleccionado
                anime({
                    targets: e.target,
                    scale: [1, 0.95, 1],
                    translateY: [0, -3, 0],
                    duration: 180,
                    easing: 'easeOutBack'
                });
            }
        }, true);
    }

    setupInputAnimations() {
        const searchInput = document.getElementById('searchInput');
        const searchBox = document.querySelector('.search-box');
        
        if (searchInput && searchBox) {
            searchInput.addEventListener('focus', () => {
                anime({
                    targets: searchBox,
                    scale: 1.02,
                    borderColor: '#8B7355',
                    duration: 250,
                    easing: 'easeOutCubic'
                });
            });

            searchInput.addEventListener('blur', () => {
                anime({
                    targets: searchBox,
                    scale: 1,
                    duration: 250,
                    easing: 'easeOutCubic'
                });
            });
        }
    }

    // Crear efecto de ondas (ripple) en botones
    createRippleEffect(element, event) {
        const rect = element.getBoundingClientRect();
        const ripple = document.createElement('div');
        
        ripple.style.position = 'absolute';
        ripple.style.borderRadius = '50%';
        ripple.style.background = 'rgba(255, 255, 255, 0.3)';
        ripple.style.pointerEvents = 'none';
        ripple.style.left = (event.clientX - rect.left - 10) + 'px';
        ripple.style.top = (event.clientY - rect.top - 10) + 'px';
        ripple.style.width = '20px';
        ripple.style.height = '20px';
        
        element.appendChild(ripple);

        anime({
            targets: ripple,
            scale: [0, 8],
            opacity: [1, 0],
            duration: 500,
            easing: 'easeOutCubic',
            complete: () => {
                ripple.remove();
            }
        });
    }

    // Animar modal
    animateModal(show = true) {
        const modal = document.querySelector('.modal');
        const modalContent = document.querySelector('.modal-content');
        
        if (show) {
            modal.style.display = 'flex';
            
            anime.timeline()
                .add({
                    targets: modal,
                    opacity: [0, 1],
                    duration: 200,
                    easing: 'easeOutCubic'
                })
                .add({
                    targets: modalContent,
                    scale: [0.7, 1],
                    opacity: [0, 1],
                    translateY: [-50, 0],
                    duration: 250,
                    easing: 'easeOutBack'
                }, '-=100');
        } else {
            anime.timeline()
                .add({
                    targets: modalContent,
                    scale: [1, 0.8],
                    opacity: [1, 0],
                    translateY: [0, 30],
                    duration: 200,
                    easing: 'easeInCubic'
                })
                .add({
                    targets: modal,
                    opacity: [1, 0],
                    duration: 150,
                    easing: 'easeInCubic',
                    complete: () => {
                        modal.style.display = 'none';
                    }
                }, '-=50');
        }
    }

    // Animar progreso de descarga
    animateProgress(percentage) {
        anime({
            targets: '#progressFill',
            width: percentage + '%',
            duration: 300,
            easing: 'easeOutCubic'
        });

        // Efecto de pulso en el texto de progreso
        anime({
            targets: '#progressText',
            scale: [1, 1.05, 1],
            duration: 200,
            easing: 'easeOutCubic'
        });
    }

    // Animar notificaciones
    animateNotification(notification, show = true) {
        if (show) {
            anime({
                targets: notification,
                translateX: [300, 0],
                opacity: [0, 1],
                scale: [0.8, 1],
                duration: 300,
                easing: 'easeOutBack'
            });
        } else {
            anime({
                targets: notification,
                translateX: [0, 300],
                opacity: [1, 0],
                scale: [1, 0.8],
                duration: 200,
                easing: 'easeInCubic'
            });
        }
    }

    // Animar loading spinner
    animateSpinner() {
        const spinner = document.querySelector('.loading-spinner');
        if (spinner) {
            anime({
                targets: spinner,
                rotate: '360deg',
                duration: 800,
                loop: true,
                easing: 'linear'
            });

            // Efecto de respiración
            anime({
                targets: spinner,
                scale: [1, 1.1, 1],
                duration: 1500,
                loop: true,
                easing: 'easeInOutQuad'
            });
        }
    }

    // Animar cambio de tabs
    animateTabChange(newTab, oldTab) {
        // Animar salida del tab anterior
        if (oldTab) {
            anime({
                targets: oldTab,
                scale: 1,
                backgroundColor: 'transparent',
                duration: 150,
                easing: 'easeOutCubic'
            });
        }

        // Animar entrada del nuevo tab
        anime({
            targets: newTab,
            scale: [1, 1.05, 1],
            duration: 200,
            easing: 'easeOutBack'
        });
    }

    // Función para reiniciar todas las animaciones
    resetAnimations() {
        anime.remove('.result-item');
        anime.remove('.logo h1');
        anime.remove('.logo p');
        anime.remove('.search-section');
        anime.remove('.quality-section');
    }

    // Manejar cambios de orientación y resize
    handleResize() {
        window.addEventListener('resize', () => {
            // Reiniciar algunas animaciones si es necesario
            const resultItems = document.querySelectorAll('.result-item');
            if (resultItems.length > 0) {
                anime.remove(resultItems);
                // Re-animar si es necesario
                setTimeout(() => {
                    this.showNewResults();
                }, 100);
            }
        });
        
        // Manejar cambio de orientación específicamente
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                // Reajustar elementos después del cambio de orientación
                window.location.reload();
            }, 500);
        });
    }
}

// Inicializar el manager de animaciones cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    window.animationManager = new AnimationManager();
});

// Exportar para uso en otros scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AnimationManager;
}
