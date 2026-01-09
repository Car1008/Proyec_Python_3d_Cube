# Testing y validación

El objetivo del testing es verificar:
- Correcta aplicación de movimientos al modelo lógico.
- Correcta sincronización entre GUI ↔ modelo ↔ render.
- Correcto funcionamiento del solver (en escenarios controlados).
- Robustez ante errores y cancelación.

## 1) Pruebas unitarias (sin GUI)

### 1.1 CubeModel (reglas básicas)
Casos recomendados:
- Reset deja el cubo resuelto.
- Aplicar `R` y luego `R'` vuelve al estado anterior.
- Aplicar `U2` dos veces vuelve al estado original.
- Secuencias cortas conocidas (`R U R' U'`) cambian el estado y luego pueden deshacerse.

Ejecutar:
```bash
python -m unittest discover -s rubik_sim/tests -p "test_*.py" -v