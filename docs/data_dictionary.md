# Dicionário de dados

## Bronze

- `ingestion_id`: UUID da execução
- `ingestion_timestamp`: timestamp UTC da gravação
- `source`: fonte dos dados (`opensky`)
- `endpoint`: endpoint consultado (`states/all`)
- `request_parameters`: parâmetros HTTP enviados
- `http_status`: status da resposta
- `response_time_ms`: tempo da resposta em ms
- `source_timestamp`: timestamp da API
- `record_count`: quantidade de registros do payload
- `payload`: resposta original JSON da API

## Silver

- `icao24`: identificador da aeronave
- `callsign`: chamada da aeronave sem espaços
- `origin_country`: país de origem
- `longitude`, `latitude`: coordenadas observadas
- `barometric_altitude_m`, `geometric_altitude_m`: altitudes
- `velocity_km_h`: velocidade convertida em km/h
- `on_ground`: se a aeronave está no solo
- `last_contact`: timestamp Unix original da OpenSky, em segundos UTC
- `last_contact_at`: timestamp tipado UTC para consumo analítico e no dashboard
- `source_timestamp`: timestamp da API
- `ingestion_id`: UUID de ingestão
- `processed_timestamp`: momento da transformação

## Gold

- `icao24`, `callsign`, `latitude`, `longitude`
- `velocity_km_h`, `baro_altitude_ft`
- `last_contact`, `last_seen_timestamp`

## Rejeitados

- `ingestion_id`: UUID de ingestão
- `rejected_timestamp`: instante da rejeição
- `reason`: motivo da rejeição
- `stage`: fase do pipeline
- `raw_record`: payload bruto original
