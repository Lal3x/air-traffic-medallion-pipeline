"""Exemplo mínimo de Pipeline, Create e Map para quem está começando no Beam."""

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions


def run() -> None:
    """Cria uma PCollection pequena e imprime cada elemento com Map."""
    options = PipelineOptions([])
    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            | "Criar mensagens" >> beam.Create(["hello", "air traffic"])
            | "Imprimir mensagens" >> beam.Map(print)
        )


if __name__ == "__main__":
    run()
