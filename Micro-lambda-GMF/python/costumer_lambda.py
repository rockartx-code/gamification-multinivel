"""Puente de compatibilidad: el módulo real es `customer_lambda`.

El nombre traía un typo (`costumer` por `customer`) y estaba fosilizado en la
configuración del handler de AWS Lambda, que vive fuera de este repositorio.
Renombrar el archivo a secas rompería el despliegue en el siguiente deploy.

Este puente permite hacerlo en dos pasos sin ventana de caída:

  1. (hecho) El código vive en `customer_lambda.py`; este módulo lo reexporta,
     así que el handler configurado hoy —`costumer_lambda.lambda_handler`—
     sigue funcionando igual.
  2. (pendiente, en AWS) Cambiar el handler de la función a
     `customer_lambda.lambda_handler` y borrar este archivo.
"""
import customer_lambda

# El handler configurado hoy en AWS apunta a este módulo.
lambda_handler = customer_lambda.lambda_handler


def __getattr__(name: str):
    """Reexporta cualquier otro símbolo del módulo real."""
    return getattr(customer_lambda, name)
