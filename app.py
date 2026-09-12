import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from io import StringIO
import matplotlib.font_manager as fm

st.set_page_config(page_title="SoccerLens 2.0", page_icon="⚽", layout="wide")
st.title("⚽ SoccerLens 2.0")
st.caption("경기를 보며 패스를 직접 입력하면 네트워크와 지표가 즉석에서 바뀝니다.")

# 한글 폰트: Streamlit Cloud에 설치된 폰트 중 가능한 것 자동 선택
available = {f.name for f in fm.fontManager.ttflist}
for candidate in ["Noto Sans CJK KR", "Noto Sans CJK JP", "NanumGothic", "Arial Unicode MS"]:
    if candidate in available:
        plt.rcParams["font.family"] = candidate
        break
plt.rcParams["axes.unicode_minus"] = False


def graph_label(name):
    labels = {
        "손흥민":"Son", "이강인":"Lee Kang-in", "황인범":"Hwang In-beom",
        "황희찬":"Hwang Hee-chan", "김민재":"Kim Min-jae", "김영권":"Kim Young-gwon",
        "정우영":"Jung Woo-young", "조규성":"Cho Gue-sung", "이재성":"Lee Jae-sung",
        "설영우":"Seol Young-woo", "조현우":"Jo Hyeon-woo"
    }
    return labels.get(name, name)

def analyze(df):
    G = nx.DiGraph()
    if not df.empty:
        for _, r in df.iterrows():
            a, b = str(r["passer"]), str(r["recipient"])
            w = float(r["count"])
            if G.has_edge(a,b):
                G[a][b]["weight"] += w
            else:
                G.add_edge(a,b,weight=w)

    for u,v,d in G.edges(data=True):
        d["distance"] = 1/d["weight"]

    bc = nx.betweenness_centrality(G, weight="distance", normalized=True) if len(G) else {}

    UG = nx.Graph()
    for u,v,d in G.edges(data=True):
        w = d["weight"]
        if UG.has_edge(u,v):
            UG[u][v]["weight"] += w
        else:
            UG.add_edge(u,v,weight=w)

    cl = nx.average_clustering(UG, weight="weight") if len(UG) > 1 else 0
    total = int(df["count"].sum()) if not df.empty else 0
    top = max(bc,key=bc.get) if bc else "-"
    topbc = bc.get(top,0)
    return G, bc, cl, total, top, topbc

def show_analysis(df, key):
    G, bc, cl, total, top, topbc = analyze(df)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("총 패스", f"{total:,}")
    c2.metric("사이중앙성 1위", top)
    c3.metric("최고 BC", f"{topbc:.4f}")
    c4.metric("평균 클러스터링", f"{cl:.4f}")

    left,right = st.columns([1.45,1])
    with left:
        st.subheader("실시간 패스 네트워크")
        if len(G):
            fig,ax = plt.subplots(figsize=(8,5.5))
            pos = nx.spring_layout(G,seed=7,weight="weight")
            ws = [G[u][v]["weight"] for u,v in G.edges()]
            mw = max(ws) if ws else 1
            widths = [1 + 5*w/mw for w in ws]
            sizes = [1800 if n==top else 1050 for n in G.nodes()]
            # pitch-like background
            ax.set_facecolor("#eef7ee")
            ax.add_patch(plt.Rectangle((-1.25,-1.0),2.5,2.0,fill=False,linewidth=1.5))
            ax.plot([0,0],[-1,1],linewidth=1)
            ax.add_patch(plt.Circle((0,0),0.22,fill=False,linewidth=1))
            nx.draw_networkx_nodes(G,pos,node_size=sizes,ax=ax)
            nx.draw_networkx_edges(G,pos,width=widths,alpha=.48,
                                   arrows=True,arrowsize=18,ax=ax)
            labels = {n: graph_label(n) for n in G.nodes()}
            nx.draw_networkx_labels(G,pos,labels=labels,font_size=9,font_weight="bold",ax=ax)
            edge_labels={(u,v):int(d["weight"]) for u,v,d in G.edges(data=True)}
            nx.draw_networkx_edge_labels(G,pos,edge_labels=edge_labels,font_size=8,ax=ax)
            if top in pos:
                x,y = pos[top]
                ax.annotate("BC #1", (x,y), xytext=(0,28), textcoords="offset points",
                            ha="center", fontsize=9, fontweight="bold")
            ax.set_xlim(-1.35,1.35)
            ax.set_ylim(-1.1,1.1)
            ax.axis("off")
            st.pyplot(fig)
            st.caption("노드 위치는 실제 경기 위치가 아니라 선수 간 연결 관계를 보기 위한 배치입니다.")
        else:
            st.info("패스를 입력하면 여기에 네트워크가 만들어집니다.")

    with right:
        st.subheader("사이중앙성 순위")
        if bc:
            rank = pd.DataFrame(sorted(bc.items(),key=lambda x:x[1],reverse=True),
                                columns=["선수","사이중앙성"])
            rank["사이중앙성"] = rank["사이중앙성"].round(4)
            st.dataframe(rank,hide_index=True,use_container_width=True)
        else:
            st.write("아직 계산할 패스가 없습니다.")

        st.subheader("자동 분석")
        if total:
            st.write(f"현재 총 {total}회의 패스가 기록되었습니다. "
                     f"{top}의 사이중앙성이 가장 높아 선수들을 연결하는 다리 역할이 "
                     f"상대적으로 크게 나타납니다. 평균 클러스터링은 {cl:.4f}입니다.")
        else:
            st.write("패스를 기록하면 분석이 자동으로 표시됩니다.")

tab1, tab2 = st.tabs(["🎮 직접 체험", "📂 CSV 분석"])

with tab1:
    st.subheader("경기를 보면서 직접 패스 기록하기")
    st.write("선수 이름을 정한 뒤 **패스한 선수 → 받은 선수 → + 패스 기록** 순서로 누르세요.")

    default_players = "손흥민,이강인,황인범,황희찬,김민재,김영권,정우영,조규성,이재성,설영우,조현우"
    player_text = st.text_input("선수 이름 (쉼표로 구분)", default_players, key="players")
    players = [x.strip() for x in player_text.split(",") if x.strip()]

    if "live_events" not in st.session_state:
        st.session_state.live_events = []

    a,b,c = st.columns([1,1,.65])
    with a:
        passer = st.selectbox("패스한 선수", players, key="passer")
    with b:
        recipients = [p for p in players if p != passer]
        recipient = st.selectbox("받은 선수", recipients, key="recipient") if recipients else None
    with c:
        st.write("")
        st.write("")
        if st.button("➕ 패스 기록", use_container_width=True, type="primary"):
            if recipient:
                st.session_state.live_events.append((passer,recipient))
                st.rerun()

    d,e,f = st.columns(3)
    with d:
        if st.button("↩️ 방금 패스 취소", use_container_width=True):
            if st.session_state.live_events:
                st.session_state.live_events.pop()
                st.rerun()
    with e:
        if st.button("🗑️ 전체 초기화", use_container_width=True):
            st.session_state.live_events = []
            st.rerun()
    with f:
        st.metric("현재 기록", f"{len(st.session_state.live_events)}회")

    if st.session_state.live_events:
        raw = pd.DataFrame(st.session_state.live_events, columns=["passer","recipient"])
        live_df = raw.value_counts(["passer","recipient"]).reset_index(name="count")
    else:
        live_df = pd.DataFrame(columns=["passer","recipient","count"])

    show_analysis(live_df, "live")

    if not live_df.empty:
        st.download_button(
            "⬇️ 현재 기록 CSV 저장",
            live_df.to_csv(index=False).encode("utf-8-sig"),
            "soccerlens_live_passes.csv",
            "text/csv",
            use_container_width=True
        )
        with st.expander("기록된 패스 보기"):
            st.dataframe(live_df.sort_values("count",ascending=False),
                         hide_index=True,use_container_width=True)

with tab2:
    st.subheader("기존 CSV 파일 분석")
    st.caption("CSV 열 이름: passer, recipient, count")
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
    uploaded = st.file_uploader("패스 CSV 업로드",type="csv",key="csv")
    df = pd.read_csv(uploaded) if uploaded else pd.read_csv(StringIO(sample))
    needed={"passer","recipient","count"}
    if needed.issubset(df.columns):
        df=df[["passer","recipient","count"]].copy()
        df["count"]=pd.to_numeric(df["count"],errors="coerce")
        df=df.dropna()
        df=df[df["count"]>0]
        show_analysis(df,"csv")
    else:
        st.error("CSV에는 passer, recipient, count 열이 필요합니다.")
