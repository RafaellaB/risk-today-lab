import json
import requests
import streamlit as st
import streamlit.components.v1 as components

# 1. Configurar a página do Streamlit (Modo Amplo e Escuro)
st.set_page_config(page_title="RISK FLOOD - Radar Real", layout="wide")

st.markdown(
    """
    <style>
    .main { background-color: #11151c; color: white; }
    h1, h2, h3, p, span { color: #ffffff !important; }
    footer {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🌧️ Radar Meteorológico Ao Vivo - Recife")
st.caption("Histórico REAL e oficial de precipitação atualizado em tempo real via RainViewer API")

# 2. Buscar o histórico real de imagens na API do RainViewer usando o Python
@st.cache_data(ttl=180)
def buscar_dados_radar_reais():
    url = "https://api.rainviewer.com/public/weather-maps.json"
    try:
        res = requests.get(url).json()
        return res
    except:
        return None

dados_api = buscar_dados_radar_reais()

if not dados_api or "radar" not in dados_api or "past" not in dados_api.get("radar", {}):
    st.error("Não foi possível conectar com o servidor do RainViewer para colher dados reais.")
else:
    json_dados_radar = json.dumps(dados_api)

    # 3. Construção do Iframe com a TRAVA de aproximação decimal (zoomSnap)
    html_mapa = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            html, body, #map {{ width: 100%; height: 100%; margin: 0; padding: 0; background: #11151c; }}
            #controls {{
                position: absolute; bottom: 30px; left: 30px; z-index: 1000;
                background: rgba(20, 24, 33, 0.95); padding: 15px 20px; border-radius: 8px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: white; 
                box-shadow: 0 4px 15px rgba(0,0,0,0.6); border: 1px solid rgba(255,255,255,0.1);
            }}
            .btn {{
                background: #ff3333; color: white; border: none; padding: 10px 20px;
                border-radius: 4px; cursor: pointer; font-weight: bold; margin-right: 12px;
                font-size: 14px; transition: background 0.2s;
            }}
            .btn:hover {{ background: #ff5555; }}
            #timeline {{ font-size: 15px; font-weight: 600; display: inline-block; min-width: 140px; vertical-align: middle; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div id="controls">
            <button class="btn" id="playBtn" onclick="togglePlay()">⏸ Pause</button>
            <span id="timeline">Sincronizando...</span>
        </div>

        <script>
            // CORREÇÃO CRUCIAL: zoomSnap e zoomDelta forçam o Leaflet a usar APENAS números inteiros de zoom
            var map = L.map('map', {{ 
                zoomControl: true,
                zoomSnap: 1,
                zoomDelta: 1
            }}).setView([-8.05428, -34.8813], 7);

            // Mapa de fundo escuro urbano público (CartoDB Dark Matter)
            L.tileLayer('https://basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; CARTO',
                maxZoom: 12,
                minZoom: 4
            }}).addTo(map);

            // Marcador operacional vermelho de Recife
            L.circleMarker([-8.05428, -34.8813], {{
                radius: 7, color: '#ff3333', fillColor: '#ff3333', fillOpacity: 1
            }}).addTo(map).bindPopup('<b>Recife</b>');

            var apiData = {json_dados_radar};
            var pastFrames = apiData.radar.past;
            
            var radarLayers = {{}};
            var currentFrameIdx = 0;
            var animationInterval = null;
            var codigoCorNOAA = 2; 

            // Pré-carrega na memória as imagens reais
            pastFrames.forEach(function(frame, index) {{
                var urlReal = 'https://tilecache.rainviewer.com' + frame.path + '/256/{{z}}/{{x}}/{{y}}/' + codigoCorNOAA + '/1_1.png';
                radarLayers[index] = L.tileLayer(urlReal, {{ opacity: 0.75, zIndex: 500 }});
            }});

            radarLayers[currentFrameIdx].addTo(map);
            atualizarTextoTimeline();

            function atualizarTextoTimeline() {{
                var timestamp = pastFrames[currentFrameIdx].time;
                var date = new Date(timestamp * 1000);
                var horas = ('0' + date.getHours()).slice(-2);
                var minutos = ('0' + date.getMinutes()).slice(-2);
                document.getElementById('timeline').innerText = 'Horário Real: ' + horas + ':' + minutos + ' UTC';
            }}

            function avancarFrame() {{
                map.removeLayer(radarLayers[currentFrameIdx]);
                currentFrameIdx = (currentFrameIdx + 1) % pastFrames.length;
                radarLayers[currentFrameIdx].addTo(map);
                atualizarTextoTimeline();
            }}

            function togglePlay() {{
                var btn = document.getElementById('playBtn');
                if (animationInterval) {{
                    clearInterval(animationInterval);
                    animationInterval = null;
                    btn.innerText = '▶️ Play';
                }} else {{
                    animationInterval = setInterval(avancarFrame, 600); 
                    btn.innerText = '⏸ Pause';
                }}
            }}

            animationInterval = setInterval(avancarFrame, 600);
        </script>
    </body>
    </html>
    """

    # 4. Injetar a janela HTML independente dentro do layout do Streamlit
    components.html(html_mapa, height=680, scrolling=False)