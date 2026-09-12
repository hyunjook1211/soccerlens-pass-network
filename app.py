import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from io import StringIO

st.set_page_config(page_title="SoccerLens", page_icon="⚽", layout="wide")
st.title("⚽ SoccerLens")
st.subheader("Pass Network Analyzer")
st.caption("CSV를 올리면 패스 수·사이중앙성·클러스터링·패스 네트워크를 자동 분석합니다.")

sample = """passer,recipient,count
황인범,손흥민,12
황인범,이강인,9
손흥민,이강인,7
이강인,황인범,8
손흥민,황희찬,6
황희찬,이강인,5
김민재,황인범,10
김영권,김민재,8
김민재,김영권,7
이강인,손흥민,6
"""

uploaded = st.file_uploader("패스 CSV 업로드", type="csv",
    help="열 이름은 passer, recipient, count 로 만들어 주세요.")
df = pd.read_csv(uploaded) if uploaded else pd.read_csv(StringIO(sample))

needed = {"passer","recipient","count"}
if not needed.issubset(df.columns):
    st.error("CSV에는 passer, recipient, count 열이 필요합니다.")
    st.stop()

df = df[["passer","recipient","count"]].copy()
df["count"] = pd.to_numeric(df["count"], errors="coerce")
df = df.dropna()
df = df[df["count"] > 0]

G = nx.DiGraph()
for _, r in df.iterrows():
    a,b,w = str(r.passer),str(r.recipient),float(r["count"])
    if G.has_edge(a,b): G[a][b]["weight"] += w
    else: G.add_edge(a,b,weight=w)

for u,v,d in G.edges(data=True):
    d["distance"] = 1/d["weight"]

bc = nx.betweenness_centrality(G, weight="distance", normalized=True)

UG = nx.Graph()
for u,v,d in G.edges(data=True):
    w=d["weight"]
    if UG.has_edge(u,v): UG[u][v]["weight"] += w
    else: UG.add_edge(u,v,weight=w)

cl = nx.average_clustering(UG, weight="weight") if len(UG)>1 else 0
total = int(df["count"].sum())
top = max(bc,key=bc.get) if bc else "-"
topbc = bc.get(top,0)

c1,c2,c3,c4=st.columns(4)
c1.metric("총 패스",f"{total:,}")
c2.metric("사이중앙성 1위",top)
c3.metric("최고 BC",f"{topbc:.4f}")
c4.metric("평균 클러스터링",f"{cl:.4f}")

left,right=st.columns([1.4,1])
with left:
    st.markdown("### 패스 네트워크")
    fig,ax=plt.subplots(figsize=(8,6))
    pos=nx.spring_layout(G,seed=7,weight="weight")
    ws=[G[u][v]["weight"] for u,v in G.edges()]
    mw=max(ws) if ws else 1
    widths=[.8+4*w/mw for w in ws]
    sizes=[1500 if n==top else 850 for n in G.nodes()]
    nx.draw_networkx_nodes(G,pos,node_size=sizes,ax=ax)
    nx.draw_networkx_edges(G,pos,width=widths,alpha=.45,arrows=True,arrowsize=16,ax=ax)
    nx.draw_networkx_labels(G,pos,font_size=10,ax=ax)
    ax.axis("off")
    st.pyplot(fig)
    st.caption("노드 위치는 실제 경기 위치가 아니라 연결 관계를 보기 위한 배치입니다.")

with right:
    st.markdown("### 사이중앙성 순위")
    rank=pd.DataFrame(sorted(bc.items(),key=lambda x:x[1],reverse=True),
                      columns=["선수","사이중앙성"])
    rank["사이중앙성"]=rank["사이중앙성"].round(4)
    st.dataframe(rank,hide_index=True,use_container_width=True)
    st.markdown("### 자동 분석")
    st.write(f"{top}의 사이중앙성이 가장 높아 선수들을 연결하는 다리 역할이 상대적으로 크게 나타났습니다. 평균 클러스터링은 {cl:.4f}입니다.")

st.markdown("### 입력 데이터")
st.dataframe(df.sort_values("count",ascending=False),hide_index=True,use_container_width=True)
