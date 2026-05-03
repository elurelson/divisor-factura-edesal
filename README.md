# Divisor de factura Edesal

Una calculadora simple para repartir una factura de luz cuando hay un consumo total compartido y un medidor interno para saber cuánto corresponde pagar por separado.

La idea es bastante directa: cargás el consumo total de la factura, el importe total y tu consumo en kWh. El programa calcula tu parte y deja el resto para la otra persona. También puede leer una factura PDF de Edesal y completar algunos campos automáticamente.

## Qué hace

- Calcula el precio promedio por kWh.
- Divide el importe según el consumo de tu medidor.
- Permite cargar un cargo fijo total y repartirlo mitad y mitad.
- Guarda un historial local de los cálculos dentro del programa.
- Genera un comprobante en texto para guardar o compartir.
- Lee PDFs de factura y detecta consumo, total, cargos fijos, cargos variables, mora e impuestos cuando el PDF tiene texto seleccionable.

## Cómo se usa

Primero instala la dependencia para leer PDFs:

```bash
pip install -r requirements.txt
```

Después ejecutá la app:

```bash
python calculadora_luz.py
```

En la ventana podés cargar los datos manualmente o usar el botón **Cargar factura PDF**. Si cargás un PDF, el programa completa:

- consumo total;
- importe total;
- cargo fijo total.

El dato que siempre tenés que cargar vos es **Mi consumo (kWh)**, porque sale de tu propio control del medidor interno.

## Cómo calcula

Si no cargás cargo fijo, reparte todo proporcionalmente por consumo:

```text
precio_por_kWh = importe_total / consumo_total_kWh
mi_importe = mi_consumo_kWh * precio_por_kWh
importe_abuela = importe_total - mi_importe
```

Si cargás cargo fijo, el programa hace esto:

```text
cargo_fijo_para_cada_uno = cargo_fijo_total / 2
importe_variable = importe_total - cargo_fijo_total
precio_por_kWh = importe_variable / consumo_total_kWh
mi_importe = mi_consumo_kWh * precio_por_kWh + cargo_fijo_para_cada_uno
importe_abuela = importe_total - mi_importe
```

## Sobre la lectura de PDFs

La lectura automática está pensada para facturas de Edesal con texto seleccionable. Si el PDF es una imagen escaneada, no va a poder leerlo sin agregar OCR.

Aunque el programa detecte los valores, conviene revisarlos antes de calcular. Las facturas pueden cambiar de formato o traer conceptos raros, como mora, ajustes o impuestos con nombres distintos.

## Archivos del proyecto

- `calculadora_luz.py`: la aplicación de escritorio.
- `requirements.txt`: dependencia necesaria para leer PDFs.
- `.gitignore`: evita subir archivos temporales y el historial local.

El historial se guarda en `historial_luz.json`, pero queda ignorado por Git porque es información local de cada usuario.
