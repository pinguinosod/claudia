# Criterios de Auditoría — Clitar Hero

## Estructura y organización
- [ ] Ningún archivo supera 150 líneas de código
- [ ] Funciones con menos de 30 líneas
- [ ] Separación clara: motor (main.py), lógica pura (scoring.py), datos (theme.py), persistencia (scores.py, config.py)
- [ ] Sin código duplicado entre módulos

## Seguridad
- [ ] Sin secretos hardcodeados
- [ ] Inputs de usuario validados (keybindings, archivos de canciones)
- [ ] Archivos JSON parseados con manejo de errores

## Testing
- [ ] scoring.py con tests unitarios completos
- [ ] analyze.py con tests para generación de charts
- [ ] Funciones puras cubiertas por tests

## Performance
- [ ] Game loop mantiene 60 FPS sin drops
- [ ] Sin cálculos pesados dentro del render loop
- [ ] Lazy loading de assets de audio

## Visual y UX
- [ ] Todos los colores definidos en theme.py (sin hex hardcodeados)
- [ ] Animaciones con easing (no lineales)
- [ ] Pantallas idle con animación de respiración
- [ ] Feedback visual en cada interacción del usuario

## Mantenibilidad
- [ ] Constantes de juego centralizadas (hit windows, scoring weights)
- [ ] Playfield math auto-calculado (sin valores hardcodeados)
- [ ] Código muerto eliminado
