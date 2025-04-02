Este projeto processa dados de praças de táxi em Lisboa, Portugal, e otimiza um problema de roteamento de veículos (VRP) para determinar a rota mais eficiente para um táxi atender múltiplos clientes. Utiliza dados geoespaciais, a API de Direções do Mapbox para estimativas de tempo de viagem com tráfego e gera uma visualização interativa em mapa usando Folium.

O projeto é composto por dois scripts principais:

taxi_data_prep.py: Pré-processa dados brutos de praças de táxi a partir de um arquivo Excel, convertendo-os para os formatos CSV e GeoJSON para análise geoespacial.Os das estradas foi retirado de "https://geodados-cml.hub.arcgis.com/datasets/CML::cartografiabase?layer=1".
main.py:
Obtém dados de tempo de viagem em tempo real usando a API de Direções do Mapbox.
Constrói um grafo da rede rodoviária de Lisboa usando dados do OpenStreetMap.
Resolve um VRP para encontrar a rota ideal partindo de uma praça de táxi, visitando locais de clientes e retornando ao ponto de origem.
Visualiza a rota em um mapa interativo com Folium.
O resultado é um arquivo HTML (mapa_final.html) que exibe a rota otimizada, o tempo de viagem e as paragens principais.

Funcionalidades
Converte dados de praças de táxi de Excel para GeoJSON.
Estima o tempo de viagem com tráfego usando a API de Direções do Mapbox.
Otimiza rotas de táxi usando a biblioteca OR-Tools.
Visualiza a rota com marcadores para o ponto de origem e paragens dos clientes em um mapa interativo.

Execute o script principal para calcular uma rota aleatória e gerar o mapa.