import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network
from database.connection import init_db
from database.repository import PaperRepository
from knowledge_graph.graph_builder import build_graph, get_subgraph
from knowledge_graph.graph_store import get_or_build_graph, rebuild_graph
from knowledge_graph.entity_extractor import extract_concepts, extract_all_concepts
from knowledge_graph.relation_detector import detect_all_relations


def render_graph():
    st.title("🕸️ 知识图谱")

    init_db()

    # ─── 操作栏 ───
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔄 重建图谱", use_container_width=True,
                      help="重新从数据库构建知识图谱"):
            with st.spinner("正在重建图谱..."):
                G = rebuild_graph()
            st.session_state.graph_G = G
            st.rerun()
    with col2:
        if st.button("🧠 提取概念", use_container_width=True,
                      help="用 AI 从论文中提取关键概念"):
            with st.spinner("正在提取概念..."):
                result = extract_all_concepts()
            st.success(f"完成: {result['processed']}/{result['total']}")
            st.rerun()
    with col3:
        if st.button("🔗 检测关系", use_container_width=True,
                      help="用 AI 检测论文间的引用/延伸/对比关系"):
            with st.spinner("正在检测论文关系（可能需要几分钟）..."):
                count = detect_all_relations()
            st.success(f"发现 {count} 个论文关系")
            st.rerun()
    with col4:
        if st.button("📊 查看统计", use_container_width=True):
            _show_stats()

    st.divider()

    # ─── 图谱渲染 ───
    _render_network()


def _render_network():
    """用 PyVis 渲染交互式图谱"""
    if "graph_G" not in st.session_state:
        st.session_state.graph_G = get_or_build_graph()

    G = st.session_state.graph_G
    if G.number_of_nodes() == 0:
        st.info("📭 知识图谱为空，请先导入论文并提取概念")
        st.caption("步骤：① 导入论文 → ② 点击「提取概念」→ ③ 点击「检测关系」→ ④ 点击「重建图谱」")
        return

    # 筛选器
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        node_type_filter = st.multiselect(
            "显示类型",
            ["paper", "concept"],
            default=["paper", "concept"],
            key="graph_filter",
        )
    with col_f2:
        concept_filter = st.multiselect(
            "按概念筛选",
            _get_concept_labels(G),
            default=[],
            key="concept_filter",
        )

    # 构建 PyVis 网络
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="#333333")
    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {"iterations": 150}
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 200,
            "navigationButtons": true
        }
    }
    """)

    # 筛选要显示的子图
    if concept_filter:
        concept_ids = [int(l.split(":")[0]) for l in concept_filter]
        display_G = get_subgraph(G, concept_ids=concept_ids, max_depth=1)
    else:
        display_G = G

    # 添加节点到 PyVis
    for node_id, node_data in display_G.nodes(data=True):
        ntype = node_data.get("type", "paper")
        if ntype not in node_type_filter:
            continue

        if ntype == "paper":
            label = node_data.get("label", node_id)[:60]
            title_text = (
                f"<b>{node_data.get('title', '')[:100]}</b><br>"
                f"Year: {node_data.get('year', '')}<br>"
                f"Venue: {node_data.get('venue', '')}<br>"
                f"Status: {node_data.get('status', '')}"
            )
            color = {"unread": "#c8e6c9", "reading": "#fff9c4", "read": "#a5d6a7"}.get(
                node_data.get("status", ""), "#e0e0e0")
            net.add_node(
                node_id, label=label, title=title_text, color=color,
                shape="box", size=20, font={"size": 12},
            )
        else:
            cat_colors = {
                "algorithm": "#ffcc80", "framework": "#ce93d8",
                "problem": "#ef9a9a", "metric": "#80cbc4",
                "theory": "#ffe082", "technique": "#b0bec5",
            }
            color = cat_colors.get(node_data.get("category", ""), "#e0e0e0")
            net.add_node(
                node_id, label=node_data.get("label", node_id)[:30],
                title=f"<b>{node_data.get('name', '')}</b><br>{node_data.get('description', '')[:200]}",
                color=color, shape="dot", size=15, font={"size": 10},
            )

    # 添加边
    for src, dst, edge_data in display_G.edges(data=True):
        if src not in net.nodes or dst not in net.nodes:
            continue
        etype = edge_data.get("type", "")
        if etype == "paper_relation":
            net.add_edge(src, dst, color="#e57373", width=2, dashes=True,
                         title=edge_data.get("relation", ""))
        elif etype == "has_concept":
            rel = edge_data.get("relevance", "")
            width = 2 if rel == "core" else 1
            net.add_edge(src, dst, color="#90caf9", width=width)
        else:
            net.add_edge(src, dst, color="#cfd8dc", width=0.5, dashes=True)

    # 生成 HTML 并嵌入
    try:
        html = net.generate_html()
        components.html(html, height=650, scrolling=True)
    except Exception as e:
        st.error(f"图谱渲染失败: {e}")

    st.caption(f"节点: {display_G.number_of_nodes()} | 边: {display_G.number_of_edges()}")


def _get_concept_labels(G) -> list[str]:
    concepts = []
    for node_id, data in G.nodes(data=True):
        if data.get("type") == "concept":
            cid = data.get("concept_id", "")
            name = data.get("name", node_id)
            concepts.append(f"{cid}: {name}")
    return sorted(concepts, key=lambda x: x.split(":")[1])


def _show_stats():
    G = st.session_state.get("graph_G")
    if not G:
        return
    papers = sum(1 for _, d in G.nodes(data=True) if d.get("type") == "paper")
    concepts = sum(1 for _, d in G.nodes(data=True) if d.get("type") == "concept")
    edges = G.number_of_edges()
    st.info(f"**图谱统计**: {papers} 篇论文, {concepts} 个概念, {edges} 条关联")
