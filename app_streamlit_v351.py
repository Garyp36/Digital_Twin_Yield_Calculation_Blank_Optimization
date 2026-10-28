import tempfile
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from nesting_backend_v351 import *

st.set_page_config(page_title="Digital Twin Yield Optimization", page_icon="🏭", layout="wide")
APP_VERSION="Streamlit 3.5.1"
GATEWAYS=[f"DR{i}" for i in range(6)]
GROUPS=["Upperbody","Underbody"]
MODULES=["Body Side Outer","Roof","Roof Front Structure","Roof Rear Structure"]
METHODS={"Bounding Box":1,"Rotated Close-Stack":2,"Alternate 0/180 Interlocking":3,"Mirror Pair":4}
FORM={"num_rows":1,"strip_length":1000.,"origin_x":6.,"x_gap":6.,"bottom_offset":6.,"top_offset":6.,"row_gap":6.,"pitch_step":1.,"run_mode":"Auto","method":"Rotated Close-Stack","angle_interval":2.,"mirror_choice":3,"include_mirror":False}
DRAW={"num_rows":1,"strip_length":1000.,"origin_x":10.,"x_gap":10.,"bottom_offset":10.,"top_offset":10.,"row_gap":10.,"pitch_step":1.,"run_mode":"Auto","method":"Rotated Close-Stack","angle_interval":2.,"mirror_choice":3,"include_mirror":False}
DEMO={
"54650001":{"part_name":"Side Sill Reinforcement","revision":"B","material_grade":"CR340","thickness_mm":1.2,"current_yield_pct":58.5},
"54650002":{"part_name":"Floor Reinforcement","revision":"A","material_grade":"DP590","thickness_mm":1.5,"current_yield_pct":61.2},
"54650003":{"part_name":"Mounting Bracket","revision":"C","material_grade":"CR4","thickness_mm":1.0,"current_yield_pct":None},
"54650004":{"part_name":"Cross Member Plate","revision":"A","material_grade":"DP780","thickness_mm":1.8,"current_yield_pct":68.2}}
PAGES=["Project Setup","Fetch Parts","Geometry Input","Nesting Parameters","Nesting Analysis","Priority Parts","Blank Optimisation"]

def prepare_part_analysis_local(part, geometry, results, project_target_pct, counters, elapsed):
    best=results[0] if results else None
    calculated=float(best["yield_pct"]) if best else None
    current=part.get("current_yield_pct")
    reference=calculated if calculated is not None else current
    shortfall=None if reference is None else float(project_target_pct)-float(reference)
    if shortfall is None: priority="Data Pending";status="Data Pending"
    elif shortfall>10: priority="Critical";status="Optimization Required"
    elif shortfall>5: priority="High";status="Optimization Required"
    elif shortfall>0: priority="Medium";status="Optimization Required"
    else: priority="Target Met";status="Target Met"
    return {
        "part_number":part["part_number"],"revision":part.get("revision","A"),
        "part_name":part.get("description",part.get("part_name","")),
        "module":st.session_state.project.get("module",""),
        "geometry_source":geometry.get("input_type",""),
        "current_yield_pct":current,"calculated_best_yield_pct":calculated,
        "reference_yield_pct":reference,"project_yield_target_pct":float(project_target_pct),
        "yield_shortfall_pct_point":shortfall,"target_status":status,"priority":priority,
        "best_method":best["method_name"] if best else "Not Available",
        "best_angle_deg":best["angle"] if best else None,
        "best_pitch_mm":best["pitch_x"] if best else None,
        "strip_width_mm":best["strip_width"] if best else None,
        "used_strip_length_mm":best["used_strip_length"] if best else None,
        "scrap_pct":None if calculated is None else 100.0-calculated,
        "iterations":counters.get("total",0),"valid_iterations":counters.get("valid",0),
        "invalid_iterations":counters.get("invalid",0),"execution_time_sec":elapsed,
    }

def create_priority_dataframe_local(analyses):
    rows=[]
    for a in analyses:
        rows.append({"Part Number":a["part_number"],"Revision":a["revision"],"Part Name":a["part_name"],
        "Module":a["module"],"Geometry Source":a["geometry_source"],"Current Yield (%)":a["current_yield_pct"],
        "Calculated Yield (%)":a["calculated_best_yield_pct"],"Reference Yield (%)":a["reference_yield_pct"],
        "Target Yield (%)":a["project_yield_target_pct"],"Shortfall (pp)":a["yield_shortfall_pct_point"],
        "Target Status":a["target_status"],"Priority":a["priority"],"Best Method":a["best_method"],
        "Best Angle (deg)":a["best_angle_deg"]})
    df=pd.DataFrame(rows)
    order={"Critical":0,"High":1,"Medium":2,"Data Pending":3,"Target Met":4}
    if not df.empty:
        df["_order"]=df["Priority"].map(order).fillna(5);df["_short"]=df["Shortfall (pp)"].fillna(-999)
        df=df.sort_values(["_order","_short"],ascending=[True,False]).drop(columns=["_order","_short"])
        df.insert(0,"Rank",range(1,len(df)+1))
    return df

def init():
    project_defaults={"project_code":"5465XXXX","project_name":"BIW Yield Optimization Demo","gateway":"DR0","group":"Upperbody","module":"Body Side Outer","yield_target_pct":65.0}
    defaults={"page":PAGES[0],"project":dict(project_defaults),"parts":[],"selected_parts":[],"geometries":{},"params":{},"param_mode":"Common","results":{},"analyses":{},"published_parts":{},"external_validation":{},"manual_optimisation":None}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
    # Migrate stale session state from older app versions instead of raising KeyError.
    if not isinstance(st.session_state.project,dict): st.session_state.project={}
    for k,v in project_defaults.items(): st.session_state.project.setdefault(k,v)

def project_target():
    return float(st.session_state.project.get("yield_target_pct",65.0))

def nav(p):st.session_state.page=p;st.rerun()
def getpart(pn):return next(x for x in st.session_state.parts if x["part_number"]==pn)

def sidebar():
    st.sidebar.title("Digital Twin for Yield Calculation and Blank Optimisation")
    st.sidebar.caption("Engineering Workflow")
    st.sidebar.caption(f"App version: {APP_VERSION}")
    for i,p in enumerate(PAGES,1):
        if st.sidebar.button(f"{i}. {p}",use_container_width=True,type="primary" if st.session_state.page==p else "secondary"):nav(p)
    if st.session_state.project:
        p=st.session_state.project;st.sidebar.divider();st.sidebar.caption(f"{p['project_code']} • {p['gateway']}");st.sidebar.caption(f"{p['group']} • {p['module']}");st.sidebar.metric("Yield Target",f"{project_target():.1f}%")
    st.sidebar.warning("Mock PLM demo")
    if st.sidebar.button("Reset Session",use_container_width=True):
        st.session_state.clear();st.rerun()

def project():
    st.title("Project Setup")
    p=st.session_state.project
    with st.form("proj"):
        c1,c2,c3=st.columns(3)
        code=c1.text_input("Project Code",p.get("project_code","5465XXXX"),help="Project code should start with 5465")
        name=c2.text_input("Project Name",p.get("project_name","BIW Yield Optimization Demo"))
        gateway=c3.selectbox("Gateway",GATEWAYS,index=GATEWAYS.index(p.get("gateway","DR0")))
        c1,c2,c3=st.columns(3);group=c1.selectbox("Group",GROUPS);module=c2.selectbox("Module",MODULES);target=c3.number_input("Project Yield Target (%)",1.,100.,float(p.get("yield_target_pct",65.)),.5)
        submit=st.form_submit_button("Save & Continue",type="primary")
    if submit:
        if not code.upper().startswith("5465"):st.error("Project Code must start with 5465.")
        else:st.session_state.project={"project_code":code.upper(),"project_name":name,"gateway":gateway,"group":group,"module":module,"yield_target_pct":target};nav("Fetch Parts")

def fetch():
    st.title("Fetch Parts from Mock PLM")
    with st.form("fetch"):
        c1,c2,c3=st.columns([2,2,1])
        number=c1.text_input("Part Number",value="5465",help="Part number should start with 5465")
        scope=c2.selectbox("Analysis Scope",["Single Part","Selected Parts / Batch"])
        c3.markdown("<div style='height:29px'></div>",unsafe_allow_html=True);go=c3.form_submit_button("Fetch from PLM",use_container_width=True,type="primary")
    if go:
        pn=number.strip().upper()
        if not pn.startswith("5465"):st.error("Part Number must start with 5465.")
        elif any(p["part_number"]==pn for p in st.session_state.parts):st.warning("Part already fetched.")
        else:
            r=dict(DEMO.get(pn,{"part_name":"Assumed PLM Description","revision":"A","material_grade":"","thickness_mm":None,"current_yield_pct":None}))
            r.update(part_number=pn,select=True,description=r["part_name"],dxf_status="Not Present");st.session_state.parts.append(r);st.success("Fetched from simulated PLM.")
    if st.session_state.parts:
        df=pd.DataFrame([{"Select":p.get("select",True),"Part Number":p["part_number"],"PLM Description":p["description"],"Revision":p["revision"],"Material":p.get("material_grade","") or "","Thickness (mm)":p.get("thickness_mm"),"Current Yield (%)":p.get("current_yield_pct"),"DXF Status":p["dxf_status"]} for p in st.session_state.parts])
        ed=st.data_editor(df,hide_index=True,use_container_width=True,disabled=["Part Number","Revision","Current Yield (%)","DXF Status"],column_config={"Select":st.column_config.CheckboxColumn(),"Thickness (mm)":st.column_config.NumberColumn(min_value=0.01)},key="parts_table")
        if st.button("Continue with Selected Parts",type="primary"):
            sel=[]
            for _,r in ed.iterrows():
                p=getpart(r["Part Number"]);p.update(select=bool(r["Select"]),description=r["PLM Description"],material_grade=r["Material"],thickness_mm=r["Thickness (mm)"])
                if p["select"]:sel.append(p["part_number"])
            if not sel:st.error("Select at least one part.")
            else:st.session_state.selected_parts=sel;nav("Geometry Input")
    st.info("Demo records: 54650001, 54650002, 54650003, 54650004. Other 5465xxxx values create assumed mock records.")

def standard_shape_points(pn):
    shapes=["Rectangle","Right Triangle","General Triangle","Trapezoid","L-Shape","T-Shape","Circle","Ellipse","Regular Polygon","Custom Coordinate Geometry"]
    shape=st.selectbox("Standard Shape",shapes,key="shape"+pn)
    if shape=="Rectangle":
        a,b=st.columns(2);L=a.number_input("Length (mm)",1.0,10000.0,200.0,key="sl"+pn);W=b.number_input("Width (mm)",1.0,10000.0,100.0,key="sw"+pn);return shape,[(0,0),(L,0),(L,W),(0,W)]
    if shape=="Right Triangle":
        a,b=st.columns(2);base=a.number_input("Base (mm)",1.0,10000.0,150.0,key="rtb"+pn);height=b.number_input("Height (mm)",1.0,10000.0,100.0,key="rth"+pn);return shape,[(0,0),(base,0),(0,height)]
    if shape=="General Triangle":
        text=st.text_input("Three points",value="0,0 150,0 50,100",key="gt"+pn);return shape,parse_points(text)
    if shape=="Trapezoid":
        a,b,c=st.columns(3);bottom=a.number_input("Bottom width",1.0,10000.0,200.0,key="tb"+pn);top=b.number_input("Top width",1.0,10000.0,120.0,key="tt"+pn);height=c.number_input("Height",1.0,10000.0,100.0,key="th"+pn);off=(bottom-top)/2;return shape,[(0,0),(bottom,0),(off+top,height),(off,height)]
    if shape=="L-Shape":
        a,b,c,d=st.columns(4);L=a.number_input("Overall length",1.0,10000.0,200.0,key="ll"+pn);H=b.number_input("Overall height",1.0,10000.0,100.0,key="lh"+pn);ht=c.number_input("Horizontal leg",.1,9999.0,25.0,key="lht"+pn);vt=d.number_input("Vertical leg",.1,9999.0,25.0,key="lvt"+pn)
        if ht>=H or vt>=L: raise ValueError("L-shape leg thickness must be less than overall dimension.")
        return shape,[(0,0),(L,0),(L,ht),(vt,ht),(vt,H),(0,H)]
    if shape=="T-Shape":
        a,b,c,d=st.columns(4);W=a.number_input("Overall width",1.0,10000.0,200.0,key="tw"+pn);H=b.number_input("Overall height",1.0,10000.0,120.0,key="theight"+pn);ft=c.number_input("Flange thickness",.1,9999.0,25.0,key="tft"+pn);stem=d.number_input("Stem width",.1,9999.0,50.0,key="ts"+pn)
        if ft>=H or stem>=W: raise ValueError("T-shape flange/stem must be less than overall dimension.")
        left=(W-stem)/2;right=left+stem;return shape,[(0,H-ft),(left,H-ft),(left,0),(right,0),(right,H-ft),(W,H-ft),(W,H),(0,H)]
    if shape=="Circle":
        a,b=st.columns(2);dia=a.number_input("Diameter",1.0,10000.0,100.0,key="cd"+pn);seg=b.number_input("Curve segment length",.1,100.0,2.0,key="cs"+pn);return shape,circle_points(dia,seg)
    if shape=="Ellipse":
        a,b,c=st.columns(3);major=a.number_input("Major diameter",1.0,10000.0,200.0,key="emaj"+pn);minor=b.number_input("Minor diameter",1.0,10000.0,100.0,key="emin"+pn);seg=c.number_input("Curve segment length",.1,100.0,2.0,key="eseg"+pn);return shape,ellipse_points(major,minor,seg)
    if shape=="Regular Polygon":
        a,b,c,d=st.columns(4);n=a.number_input("Sides",3,50,6,key="rpn"+pn);mode=b.selectbox("Size definition",["Circumscribed radius","Inscribed radius","Side length"],key="rpm"+pn);value=c.number_input("Size value",.1,10000.0,50.0,key="rpv"+pn);angle=d.number_input("Starting angle",-360.0,360.0,0.0,key="rpa"+pn);return shape,regular_polygon_points(int(n),value,{"Circumscribed radius":1,"Inscribed radius":2,"Side length":3}[mode],angle)
    text=st.text_area("Custom ordered X,Y points",value="0,0 0,100 25,100 25,25 200,25 200,0",key="custom"+pn);return shape,parse_points(text)

def geometry():
    st.title("Geometry Input")
    for pn in st.session_state.selected_parts:
        p=getpart(pn)
        with st.expander(f"{pn} • {p['description']} • Rev {p['revision']}",expanded=True):
            st.error("DXF not present in simulated PLM.")
            src=st.radio("Geometry source",["Upload DXF","Standard Shapes","Manual Coordinates"],horizontal=True,key="src"+pn)
            try:
                if src=="Upload DXF":
                    up=st.file_uploader("Upload DXF",type="dxf",key="up"+pn);seg=st.number_input("DXF segment length",.1,100.,1.,key="seg"+pn)
                    if up and st.button("Validate DXF",key="vd"+pn):
                        with tempfile.NamedTemporaryFile(suffix=".dxf",delete=False) as f:f.write(up.getbuffer());path=f.name
                        try:pts=import_complex_outer_points_from_dxf(path,seg) if dxf_has_curved_geometry(path) else import_simple_outer_points_from_dxf(path)
                        except Exception:pts=import_complex_outer_points_from_dxf(path,seg)
                        poly,pts=create_valid_polygon(pts,pn);st.session_state.geometries[pn]={"name":p["description"],"input_type":"DXF","source":up.name,"segment_length":seg,"points":pts,"polygon":poly,"area":poly.area}
                elif src=="Standard Shapes":
                    shape,pts=standard_shape_points(pn)
                    st.code(format_points(pts),language=None)
                    if st.button("Validate Standard Shape",key="vs"+pn):
                        poly,pts=create_valid_polygon(pts,pn);st.session_state.geometries[pn]={"name":p["description"],"input_type":"Standard Shape","source":shape,"segment_length":None,"points":pts,"polygon":poly,"area":poly.area}
                else:
                    tx=st.text_area("Ordered X,Y points","0,0 100,0 100,50 0,50",key="tx"+pn)
                    if st.button("Validate Coordinates",key="vc"+pn):
                        pts=parse_points(tx);poly,pts=create_valid_polygon(pts,pn);st.session_state.geometries[pn]={"name":p["description"],"input_type":"Coordinates","source":"Manual","segment_length":None,"points":pts,"polygon":poly,"area":poly.area}
                if pn in st.session_state.geometries:st.success(f"Valid • Area {st.session_state.geometries[pn]['area']:.2f} mm²")
            except Exception as e:st.error(str(e))
    if st.button("Continue to Nesting Parameters",type="primary"):
        miss=[x for x in st.session_state.selected_parts if x not in st.session_state.geometries]
        if miss:st.error("Validate geometry for "+", ".join(miss))
        else:nav("Nesting Parameters")

def parameter_controls(key_prefix, title, saved=None):
    saved=saved or {}
    st.subheader(title)
    part_type=st.selectbox("Part Type",["Form","Draw"],index=0 if saved.get("part_type","Form")=="Form" else 1,key=f"ptype_{key_prefix}")
    defaults=dict(FORM if part_type=="Form" else DRAW)
    defaults.update(saved)

    c1,c2,c3=st.columns(3)
    num_rows=c1.number_input("Number of Rows",min_value=1,value=int(defaults["num_rows"]),step=1,key=f"rows_{key_prefix}")
    strip_length=c2.number_input("Available Strip Length (mm)",min_value=1.0,value=float(defaults["strip_length"]),key=f"strip_{key_prefix}")
    pitch_step=c3.selectbox("Pitch Search Step (mm)",[0.5,1.0,2.0],index=[0.5,1.0,2.0].index(float(defaults["pitch_step"])) if float(defaults["pitch_step"]) in [0.5,1.0,2.0] else 1,key=f"pitch_{key_prefix}")

    c1,c2,c3=st.columns(3)
    origin_x=c1.number_input("First Blank X-Offset (mm)",min_value=0.0,value=float(defaults["origin_x"]),help="Distance from the left strip datum to the start of the first blank.",key=f"origin_{key_prefix}")
    x_gap=c2.number_input("Minimum Blank-to-Blank Gap (mm)",min_value=0.0,value=float(defaults["x_gap"]),key=f"xgap_{key_prefix}")
    row_gap=c3.number_input("Inter-Row Gap (mm)",min_value=0.0,value=float(defaults["row_gap"]),disabled=num_rows==1,key=f"rowgap_{key_prefix}")

    c1,c2=st.columns(2)
    bottom_offset=c1.number_input("Bottom Strip-Edge Offset (mm)",min_value=0.0,value=float(defaults["bottom_offset"]),key=f"bottom_{key_prefix}")
    top_offset=c2.number_input("Top Strip-Edge Offset (mm)",min_value=0.0,value=float(defaults["top_offset"]),key=f"top_{key_prefix}")

    run_mode=st.radio("Run Mode",["Auto","Manual"],index=0 if saved.get("run_mode","Auto")=="Auto" else 1,horizontal=True,key=f"mode_{key_prefix}")
    method="Auto Select Best Method"
    angle_interval=2.0
    mirror_choice=3
    include_mirror=False

    if run_mode=="Auto":
        st.info("Auto mode evaluates Bounding Box, Rotated Close-Stack, Alternate 0°/180°, and optionally Mirror Pair. Search resolution is fixed at 10° coarse → 2° fine around the best candidates.")
        st.text_input("Nesting Method",value="Auto Select Best Method",disabled=True,key=f"automethod_{key_prefix}")
        include_mirror=st.checkbox("Evaluate Mirror Layouts in Auto Mode",value=bool(saved.get("include_mirror",False)),key=f"automirror_{key_prefix}")
    else:
        method=st.selectbox("Manual Nesting Method",list(METHODS),index=list(METHODS).index(saved.get("method","Bounding Box")) if saved.get("method","Bounding Box") in METHODS else 0,key=f"method_{key_prefix}")
        if method=="Bounding Box":
            st.caption("Bounding Box uses the basic orientation logic. Manual angle interval and mirror direction are not applicable.")
        elif method in ["Rotated Close-Stack","Alternate 0/180 Interlocking"]:
            angle_interval=st.number_input("Manual Angle Search Interval (degrees)",min_value=0.0,max_value=360.0,value=float(saved.get("angle_interval",2.0)),help="Smaller angle intervals evaluate more orientations and need more execution time.",key=f"angle_{key_prefix}")
        else:
            angle_interval=st.number_input("Manual Angle Search Interval (degrees)",min_value=0.0,max_value=360.0,value=float(saved.get("angle_interval",2.0)),key=f"angle_{key_prefix}")
            mirror_label=st.selectbox("Manual Mirror Direction",["Vertical Mirror (left-right)","Horizontal Mirror (top-bottom)","Check Both"],index={1:0,2:1,3:2}.get(int(saved.get("mirror_choice",3)),2),key=f"mirror_{key_prefix}")
            mirror_choice={"Vertical Mirror (left-right)":1,"Horizontal Mirror (top-bottom)":2,"Check Both":3}[mirror_label]

    return {"part_type":part_type,"num_rows":int(num_rows),"strip_length":float(strip_length),"origin_x":float(origin_x),"x_gap":float(x_gap),"bottom_offset":float(bottom_offset),"top_offset":float(top_offset),"row_gap":0.0 if num_rows==1 else float(row_gap),"pitch_step":float(pitch_step),"run_mode":run_mode,"method":method,"angle_interval":float(angle_interval),"mirror_choice":int(mirror_choice),"include_mirror":bool(include_mirror)}

def parameters():
    st.title("Part Type, Method & Nesting Parameters")
    if not st.session_state.selected_parts:
        st.warning("Select parts first.");return
    mode=st.radio("Parameter Logic",["Common Parameters","Different Parameters per Part"],horizontal=True,key="parameter_logic")
    collected={}
    if mode=="Common Parameters":
        st.info("The common values below will be copied to every selected part. Actual part numbers remain visible in the application and analysis results.")
        existing=st.session_state.params.get(st.session_state.selected_parts[0],{})
        common=parameter_controls("common","Common Parameters for Selected Parts",existing)
        st.markdown("**Parts receiving these parameters:** " + ", ".join(st.session_state.selected_parts))
        collected={pn:dict(common) for pn in st.session_state.selected_parts}
    else:
        for pn in st.session_state.selected_parts:
            part=getpart(pn)
            with st.expander(f"{pn} • {part['description']}",expanded=True):
                collected[pn]=parameter_controls(pn,f"Parameters for {pn}",st.session_state.params.get(pn,{}))

    if st.button("Save Parameters & Continue",type="primary"):
        st.session_state.params=collected
        st.session_state.param_mode=mode
        nav("Nesting Analysis")

def settings_from(p):
    if p["run_mode"]=="Auto":
        return {"run_mode":2,"pitch_step":p["pitch_step"],"include_mirror":p["include_mirror"],"coarse_step":10,"fine_step":2,"fine_window":10,"top_coarse_angles":3}
    return {"run_mode":1,"pitch_step":p["pitch_step"],"include_mirror":True,"coarse_step":10,"fine_step":2,"fine_window":10,"top_coarse_angles":3,"manual_method":METHODS[p["method"]],"manual_angle_interval":p["angle_interval"],"manual_mirror_choice":p["mirror_choice"]}

def actual_plot(result,strip_length,title):
    fig,ax=plt.subplots(figsize=(13,4.5));plot_nesting_on_axis(ax,result,strip_length,title);fig.tight_layout();return fig

def analysis():
    st.title("Nesting Analysis & Graphical Results")
    if st.button("Run Actual Nesting Analysis",type="primary"):
        st.session_state.results={};st.session_state.analyses={};bar=st.progress(0)
        for i,pn in enumerate(st.session_state.selected_parts,1):
            p=st.session_state.params[pn];pars={k:p[k] for k in ["num_rows","origin_x","bottom_offset","top_offset","x_gap","row_gap","strip_length"]};res,cnt,t=run_geometry_nesting(st.session_state.geometries[pn],pars,settings_from(p));st.session_state.results[pn]=res
            part=getpart(pn);st.session_state.analyses[pn]=prepare_part_analysis_local(part,st.session_state.geometries[pn],res,project_target(),cnt,t);bar.progress(i/len(st.session_state.selected_parts))
    for pn,res in st.session_state.results.items():
        with st.expander(f"{pn} • {getpart(pn)['description']}",expanded=True):
            if not res:st.error("No valid result.");continue
            b=res[0];a,c,d,e=st.columns(4);a.metric("Yield",f"{b['yield_pct']:.2f}%");c.metric("Method",b["method_name"]);d.metric("Angle",f"{b['angle']:.2f}°");e.metric("Quantity",b["total_qty"])
            st.pyplot(actual_plot(b,st.session_state.params[pn]["strip_length"],f"Best Layout • {pn} • {b['method_name']} • Yield {b['yield_pct']:.2f}%"),clear_figure=True)
            table=pd.DataFrame([{"Rank":i+1,"Method":r["method_name"],"Details":r["display_name"],"Angle":r["angle"],"Quantity":r["total_qty"],"Pitch":r["pitch_x"],"Strip Width":r["strip_width"],"Used Length":r["used_strip_length"],"Yield (%)":r["yield_pct"]} for i,r in enumerate(res[:4])]);st.dataframe(table,hide_index=True,use_container_width=True)
            if st.checkbox("Show graphical Top 4 layouts",key="plots"+pn):
                fig,axes=plt.subplots(2,2,figsize=(16,9));axes=axes.flatten()
                for i,r in enumerate(res[:4]):plot_nesting_on_axis(axes[i],r,st.session_state.params[pn]["strip_length"],f"Rank {i+1}: {r['method_name']} | {r['yield_pct']:.2f}%")
                for j in range(len(res[:4]),4):axes[j].axis('off')
                fig.tight_layout();st.pyplot(fig,clear_figure=True)
    if st.session_state.results:
        st.divider()
        st.subheader("Publish Analysis Results to Mock PLM")
        st.caption("This demonstration records a publication status locally in the current session. No live PLM connector is used.")
        publish_parts=st.multiselect("Select analyzed parts to publish",st.session_state.selected_parts,default=st.session_state.selected_parts,key="publish_analysis_parts")
        c1,c2=st.columns([1,3])
        if c1.button("Publish Results to PLM",type="primary",use_container_width=True):
            if not publish_parts:
                st.error("Select at least one analyzed part to publish.")
            else:
                from datetime import datetime
                stamp=datetime.now().strftime("%d-%b-%Y %H:%M:%S")
                for pn in publish_parts:
                    best=st.session_state.results[pn][0] if st.session_state.results.get(pn) else None
                    st.session_state.published_parts[pn]={"status":"Published to Mock PLM","published_on":stamp,"yield_pct":best["yield_pct"] if best else None,"method":best["method_name"] if best else None}
                st.success(f"Results for {len(publish_parts)} part(s) published successfully to Mock PLM on {stamp}.")
        published=[pn for pn in st.session_state.selected_parts if pn in st.session_state.published_parts]
        if published:
            c2.info("Published status: " + ", ".join(f"{pn} ✓" for pn in published))
        if st.button("Continue to Priority Parts",type="secondary"):nav("Priority Parts")

def priority():
    st.title("Priority Parts and External Yield Validation")
    if not st.session_state.analyses:
        st.warning("Run analysis first.");return
    df=create_priority_dataframe_local(list(st.session_state.analyses.values()))
    st.dataframe(df,hide_index=True,use_container_width=True)
    allmet=all(x["target_status"]=="Target Met" for x in st.session_state.analyses.values())
    (st.success if allmet else st.error)("All selected parts meet target." if allmet else "Priority optimization is required.")

    st.divider()
    st.subheader("Cost Engineering and Supplier Inputs")
    st.caption("Upload blank-layout evidence and enter yield values independently for comparison with the internally calculated yield.")
    priority_parts=[pn for pn,a in st.session_state.analyses.items() if a["priority"]!="Target Met"]
    review_parts=priority_parts or list(st.session_state.analyses.keys())
    for pn in review_parts:
        part=getpart(pn);analysis_record=st.session_state.analyses[pn]
        with st.expander(f"{pn} • {part['description']} • {analysis_record['priority']}",expanded=True):
            saved=st.session_state.external_validation.get(pn,{})
            c1,c2=st.columns(2)
            with c1:
                st.markdown("#### Cost Engineering")
                cost_layout=st.file_uploader("Upload Cost Engineering blank layout",type=["png","jpg","jpeg","pdf","dxf","csv","xlsx"],key=f"cost_file_{pn}")
                cost_yield=st.number_input("Cost Engineering Yield (%)",min_value=0.0,max_value=100.0,value=float(saved.get("cost_yield",0.0)),step=0.1,key=f"cost_yield_{pn}")
            with c2:
                st.markdown("#### Supplier")
                supplier_layout=st.file_uploader("Upload Supplier blank layout",type=["png","jpg","jpeg","pdf","dxf","csv","xlsx"],key=f"supplier_file_{pn}")
                supplier_yield=st.number_input("Supplier Yield (%)",min_value=0.0,max_value=100.0,value=float(saved.get("supplier_yield",0.0)),step=0.1,key=f"supplier_yield_{pn}")
            if st.button("Save External Inputs",key=f"save_external_{pn}"):
                calculated=analysis_record.get("calculated_best_yield_pct")
                st.session_state.external_validation[pn]={"cost_yield":cost_yield,"cost_file":cost_layout.name if cost_layout else saved.get("cost_file"),"supplier_yield":supplier_yield,"supplier_file":supplier_layout.name if supplier_layout else saved.get("supplier_file"),"cost_delta":None if calculated is None or cost_yield==0 else cost_yield-calculated,"supplier_delta":None if calculated is None or supplier_yield==0 else supplier_yield-calculated}
                st.success("Cost Engineering and Supplier inputs saved for comparison.")
            ext=st.session_state.external_validation.get(pn)
            if ext:
                calculated=analysis_record.get("calculated_best_yield_pct")
                comparison=pd.DataFrame([
                    {"Source":"Internal Digital Twin","Yield (%)":calculated,"Difference vs Internal (pp)":0.0,"Layout File":"Generated by tool"},
                    {"Source":"Cost Engineering","Yield (%)":ext["cost_yield"] if ext["cost_yield"]>0 else None,"Difference vs Internal (pp)":ext["cost_delta"],"Layout File":ext.get("cost_file") or "Not uploaded"},
                    {"Source":"Supplier","Yield (%)":ext["supplier_yield"] if ext["supplier_yield"]>0 else None,"Difference vs Internal (pp)":ext["supplier_delta"],"Layout File":ext.get("supplier_file") or "Not uploaded"},
                ])
                st.dataframe(comparison,hide_index=True,use_container_width=True)

    st.divider()
    if st.button("Proceed for Blank Optimisation",type="primary",use_container_width=True):
        nav("Blank Optimisation")

def chamfer_convex_corners(polygon, chamfer_value, tolerance=1e-9):
    """Chamfer convex exterior corners by setback distance along adjacent edges.

    Concave/re-entrant corners are preserved. The setback is limited to 45% of
    the shorter adjacent edge to prevent adjacent chamfers crossing each other.
    """
    if chamfer_value <= 0:
        raise ValueError("Chamfer value must be greater than zero.")
    coords=list(polygon.exterior.coords)[:-1]
    if len(coords)<3:
        raise ValueError("At least three polygon corners are required.")
    signed=polygon_signed_area(coords)
    orientation=1 if signed>0 else -1
    revised=[];chamfered=0;skipped=[]
    for i,curr in enumerate(coords):
        prev=coords[i-1];nxt=coords[(i+1)%len(coords)]
        v1=(prev[0]-curr[0],prev[1]-curr[1]);v2=(nxt[0]-curr[0],nxt[1]-curr[1])
        l1=(v1[0]**2+v1[1]**2)**0.5;l2=(v2[0]**2+v2[1]**2)**0.5
        if l1<=tolerance or l2<=tolerance:
            skipped.append(i+1);continue
        incoming=(curr[0]-prev[0],curr[1]-prev[1]);outgoing=(nxt[0]-curr[0],nxt[1]-curr[1])
        cross=incoming[0]*outgoing[1]-incoming[1]*outgoing[0]
        is_convex=(cross*orientation)>tolerance
        if not is_convex:
            revised.append(curr);skipped.append(i+1);continue
        setback=min(float(chamfer_value),0.45*l1,0.45*l2)
        if setback<=tolerance:
            revised.append(curr);skipped.append(i+1);continue
        p1=(curr[0]+v1[0]/l1*setback,curr[1]+v1[1]/l1*setback)
        p2=(curr[0]+v2[0]/l2*setback,curr[1]+v2[1]/l2*setback)
        revised.extend([p1,p2]);chamfered+=1
    if chamfered==0:
        raise ValueError("No eligible convex corners were found for chamfering.")
    revised_polygon,revised_points=create_valid_polygon(revised,"Chamfered Geometry")
    if revised_polygon.area>=polygon.area:
        raise ValueError("Chamfer operation did not reduce blank area; revised geometry was rejected.")
    return revised_polygon,revised_points,chamfered,skipped

def optimisation_settings_for_part(pn):
    original=st.session_state.params[pn]
    return {"run_mode":2,"pitch_step":original["pitch_step"],"include_mirror":original.get("include_mirror",False),"coarse_step":10,"fine_step":2,"fine_window":10,"top_coarse_angles":3}

def blank_optimisation():
    st.title("Blank Optimisation")
    if not st.session_state.analyses:
        st.warning("Run nesting analysis first.");return
    mode=st.radio("Optimisation Mode",["Manual Optimisation","AI-Based Optimisation"],horizontal=True,key="optimisation_mode")
    priority_parts=[pn for pn,a in st.session_state.analyses.items() if a["priority"]!="Target Met"]
    candidates=priority_parts or list(st.session_state.analyses.keys())

    if mode=="AI-Based Optimisation":
        st.info("AI-based optimisation is reserved for the next development phase. Current structured inputs include calculated yield, project target, Cost Engineering yield, Supplier yield, best method, and uploaded layout references.")
        rows=[]
        for pn in candidates:
            a=st.session_state.analyses[pn];ext=st.session_state.external_validation.get(pn,{})
            rows.append({"Part Number":pn,"Part Name":a["part_name"],"Internal Yield (%)":a["calculated_best_yield_pct"],"Target (%)":a["project_yield_target_pct"],"Shortfall (pp)":a["yield_shortfall_pct_point"],"Priority":a["priority"],"Best Method":a["best_method"],"Cost Engg Yield (%)":ext.get("cost_yield"),"Supplier Yield (%)":ext.get("supplier_yield")})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        st.subheader("Planned AI Suggestion Categories")
        st.markdown("""
- Alternative blank orientation and nesting method
- Pitch and strip-width optimisation
- Mirror/alternate-layout feasibility
- Blank-contour or part-geometry opportunity areas
- Expected yield and scrap improvement
- Supplier and Cost Engineering constraint reconciliation
""")
        return

    st.info("Manual chamfer removes material at eligible convex exterior corners. Concave/re-entrant corners are preserved. Each setback is limited to 45% of the shorter adjacent edge to avoid crossing adjacent chamfers.")
    pn=st.selectbox("Select Part for Manual Optimisation",candidates,format_func=lambda x:f"{x} • {getpart(x)['description']}")
    chamfer=st.number_input("Chamfer Setback Value (mm)",min_value=0.1,value=5.0,step=0.5,help="Distance measured from each eligible corner along both adjacent edges.")
    show_layouts=st.checkbox("Show Existing and Revised Layouts",value=True)
    if st.button("Apply Chamfer and Recalculate Auto Yield",type="primary"):
        try:
            existing_geometry=st.session_state.geometries[pn]
            revised_poly,revised_points,count,skipped=chamfer_convex_corners(existing_geometry["polygon"],chamfer)
            revised_geometry={"name":existing_geometry["name"]+" - Chamfered","input_type":"Manual Optimisation","source":f"Chamfer {chamfer:.2f} mm","segment_length":None,"points":revised_points,"polygon":revised_poly,"area":revised_poly.area}
            p=st.session_state.params[pn]
            pars={k:p[k] for k in ["num_rows","origin_x","bottom_offset","top_offset","x_gap","row_gap","strip_length"]}
            revised_results,counters,elapsed=run_geometry_nesting(revised_geometry,pars,optimisation_settings_for_part(pn))
            if not revised_results:raise ValueError("Chamfered geometry produced no valid nesting solution.")
            st.session_state.manual_optimisation={"part_number":pn,"chamfer":chamfer,"geometry":revised_geometry,"results":revised_results,"chamfered_corners":count,"skipped_corners":skipped,"elapsed":elapsed}
            st.success(f"Chamfer applied to {count} convex corner(s). Revised Auto Nesting completed successfully.")
        except Exception as exc:
            st.error(str(exc))

    opt=st.session_state.get("manual_optimisation")
    if opt and opt["part_number"]==pn:
        existing=st.session_state.results[pn][0];revised=opt["results"][0]
        improvement=revised["yield_pct"]-existing["yield_pct"]
        area_reduction=st.session_state.geometries[pn]["area"]-opt["geometry"]["area"]
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Existing Auto Yield",f"{existing['yield_pct']:.2f}%")
        c2.metric("Revised Auto Yield",f"{revised['yield_pct']:.2f}%",delta=f"{improvement:+.2f} pp")
        c3.metric("Blank Area Reduction",f"{area_reduction:.2f} mm²")
        c4.metric("Chamfered Corners",opt["chamfered_corners"])
        comparison=pd.DataFrame([
            {"Condition":"Existing","Blank Area (mm²)":st.session_state.geometries[pn]["area"],"Best Method":existing["method_name"],"Angle (deg)":existing["angle"],"Pitch (mm)":existing["pitch_x"],"Quantity":existing["total_qty"],"Yield (%)":existing["yield_pct"]},
            {"Condition":"Revised Chamfered","Blank Area (mm²)":opt["geometry"]["area"],"Best Method":revised["method_name"],"Angle (deg)":revised["angle"],"Pitch (mm)":revised["pitch_x"],"Quantity":revised["total_qty"],"Yield (%)":revised["yield_pct"]},
        ])
        st.dataframe(comparison,hide_index=True,use_container_width=True)
        if show_layouts:
            c1,c2=st.columns(2)
            with c1:
                st.markdown("#### Existing Best Layout")
                st.pyplot(actual_plot(existing,st.session_state.params[pn]["strip_length"],f"Existing • {existing['method_name']} • {existing['yield_pct']:.2f}%"),clear_figure=True)
            with c2:
                st.markdown("#### Revised Chamfered Best Layout")
                st.pyplot(actual_plot(revised,st.session_state.params[pn]["strip_length"],f"Revised • {revised['method_name']} • {revised['yield_pct']:.2f}%"),clear_figure=True)
        st.caption("Engineering review is required before accepting any geometry modification. The result represents blank-layout mathematics only, not forming feasibility, strength, joining, durability, or manufacturing approval.")

init();sidebar();{"Project Setup":project,"Fetch Parts":fetch,"Geometry Input":geometry,"Nesting Parameters":parameters,"Nesting Analysis":analysis,"Priority Parts":priority,"Blank Optimisation":blank_optimisation}[st.session_state.page]()
