# Dicionário de dados

Este contrato corresponde ao coletor, ao schema Arrow em `src/air_traffic_beam/schemas/silver.py` e às transformações atuais.

## Bronze: um envelope por resposta

| Campo | Conteúdo |
| --- | --- |
| `_metadata.source` | `opensky_network` |
| `_metadata.endpoint` | `/states/all` |
| `_metadata.ingested_at` | String ISO 8601 no fuso `America/Sao_Paulo` |
| `_metadata.execution_id` | UUID comum às respostas da mesma coleta |
| `_metadata.collection_number` | Número sequencial da resposta, começando em 1 |
| `_metadata.schema_version` | Versão do envelope, atualmente `1` |
| `_metadata.bounding_box` | Objeto com `lat_min`, `lon_min`, `lat_max`, `lon_max` |
| `payload.time` | Instante da resposta em epoch Unix (segundos) |
| `payload.states` | Lista de vetores posicionais retornados pela API |

O cliente converte `states: null` (ou ausente) em `[]` antes da gravação. Os vetores são preservados, mas a Bronze não é uma cópia byte a byte da resposta HTTP. Status HTTP e tempo da requisição não são campos do envelope.

## Silver: uma observação por aeronave

| Campo | Tipo Arrow | Significado |
| --- | --- | --- |
| `icao24` | string | Identificador da aeronave |
| `callsign` | string | Indicativo com espaços nas extremidades removidos; vazio vira nulo |
| `origin_country` | string | País informado pela fonte |
| `time_position` | int64 | Instante da posição, epoch em segundos |
| `last_contact` | int64 | Instante do último contato, epoch em segundos |
| `last_contact_at` | timestamp[us, America/Sao_Paulo] | Último contato convertido para data/hora com fuso |
| `longitude`, `latitude` | float64 | Coordenadas em graus |
| `barometric_altitude_m`, `geometric_altitude_m` | float64 | Altitudes em metros |
| `on_ground` | bool | Indicador de aeronave no solo |
| `velocity_mps` | float64 | Velocidade em metros por segundo |
| `velocity_kmh` | float64 | `velocity_mps × 3.6` |
| `true_track_degrees` | float64 | Direção de deslocamento em graus |
| `vertical_rate_mps` | float64 | Razão vertical em metros por segundo |
| `squawk` | string | Código do transponder |
| `special_purpose_indicator` | bool | Indicador especial informado pela fonte |
| `position_source`, `aircraft_category` | int64 | Códigos de origem da posição e categoria |
| `source_time` | int64 | `time_position` quando disponível; caso contrário, `payload.time` |
| `ingested_at` | string | Instante de ingestão copiado dos metadados Bronze |
| `execution_id` | string | Identificador copiado dos metadados Bronze |

Identificador e coordenadas são validados; medições opcionais podem ser nulas. As altitudes permanecem em metros. Os epochs representam instantes absolutos; o fuso é aplicado em `last_contact_at` e na apresentação.

## Gold: latest

Mantém os campos Silver do registro com maior `last_contact` para cada `icao24` entre as entradas processadas. As datas são serializadas como strings em JSONL. Em empate, a seleção não define um critério adicional determinístico.

## Gold: traffic

| Campo | Significado |
| --- | --- |
| `aircraft_observations` | Total de registros Silver de entrada |
| `unique_aircraft` | Quantidade de `icao24` distintos |
| `airborne_aircraft` | Observações com `on_ground=false`, incluindo repetições de uma aeronave |
| `on_ground_aircraft` | Observações com `on_ground=true` |
| `average_velocity_kmh` | Média das velocidades não nulas, em km/h |
| `average_geometric_altitude_m` | Média das altitudes geométricas não nulas, em metros |
| `latest_contact` | Maior `last_contact` da entrada |

O resumo usa todas as observações, não apenas a visão `latest`. Por exemplo, três observações em voo da mesma aeronave resultam em `aircraft_observations=3`, `unique_aircraft=1` e `airborne_aircraft=3`.

## Rejeitados

Os JSONL de rejeição contêm `record` e `rejection_reason`. Para JSON inválido, contêm `raw_record`, `rejection_reason=invalid_json` e `error_message`. Não há um conjunto fixo de campos de timestamp ou identificador acrescentado a todas as rejeições.

Motivos incluem `invalid_envelope`, `invalid_states`, `invalid_state_vector`, `state_vector_too_short`, `missing_aircraft_identifier`, `missing_coordinates`, `invalid_coordinates_type`, `latitude_out_of_range` e `longitude_out_of_range`.

O contrato de métricas está em [Logs e relatórios](reports.md).
