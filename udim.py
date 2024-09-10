import maya.cmds as cmds
import maya.api.OpenMaya as om
from collections import defaultdict

def get_materials_udim_map():
    materials = cmds.ls(materials=True)
    material_udim_map = {}
    
    for material in materials:
        print(f"Processing material: {material}")
        shading_engines = cmds.listConnections(material, type='shadingEngine') or []
        
        udim_set = set()
        for shading_engine in shading_engines:
            connected_meshes = cmds.listConnections(shading_engine, type='mesh') or []

            for mesh in connected_meshes:
                try:
                    sel_list = om.MSelectionList()
                    sel_list.add(mesh)
                    dag_path = sel_list.getDagPath(0)
                    mesh_fn = om.MFnMesh(dag_path)
                    
                    uv_sets = mesh_fn.getUVSetNames()
                    if not uv_sets:
                        continue
                    
                    for i in range(mesh_fn.numPolygons):
                        for j in range(mesh_fn.getPolygonUVid(i, 0)):
                            u, v = mesh_fn.getUV(j, uv_sets[0])
                            udim = 1001 + int(u) + (int(v) * 10)
                            udim_set.add(udim)
                except Exception as e:
                    print(f"Error processing mesh {mesh}: {str(e)}")
        
        if udim_set:
            material_udim_map[material] = sorted(udim_set)
    
    return material_udim_map

def identify_shared_udims(material_udim_map):
    shared_udims = {}
    for material, udims in material_udim_map.items():
        for udim in udims:
            if udim not in shared_udims:
                shared_udims[udim] = []
            shared_udims[udim].append(material)
    
    return {udim: materials for udim, materials in shared_udims.items() if len(materials) > 1}

def check_uv_overlap(material_udim_map):
    udim_mesh_map = {}
    overlap_info = defaultdict(lambda: defaultdict(set))
    reported_overlaps = set()
    
    for material, udims in material_udim_map.items():
        shading_engines = cmds.listConnections(material, type='shadingEngine') or []
        for shading_engine in shading_engines:
            meshes = cmds.listConnections(shading_engine, type='mesh') or []
            for mesh in meshes:
                for udim in udims:
                    if udim not in udim_mesh_map:
                        udim_mesh_map[udim] = []
                    udim_mesh_map[udim].append((mesh, material))
    
    for udim, mesh_material_pairs in udim_mesh_map.items():
        uv_bboxes = []
        for mesh, material in mesh_material_pairs:
            try:
                sel_list = om.MSelectionList()
                sel_list.add(mesh)
                dag_path = sel_list.getDagPath(0)
                mesh_fn = om.MFnMesh(dag_path)
                
                uv_sets = mesh_fn.getUVSetNames()
                if not uv_sets:
                    continue
                
                u_values, v_values = mesh_fn.getUVs(uv_sets[0])
                
                for face_id in range(mesh_fn.numPolygons):
                    face_vertex_ids = mesh_fn.getPolygonVertices(face_id)
                    face_uv_ids = [mesh_fn.getPolygonUVid(face_id, i) for i in range(len(face_vertex_ids))]
                    
                    u_min = min(u_values[i] for i in face_uv_ids)
                    u_max = max(u_values[i] for i in face_uv_ids)
                    v_min = min(v_values[i] for i in face_uv_ids)
                    v_max = max(v_values[i] for i in face_uv_ids)
                    
                    # Check if the face is in the current UDIM
                    if int(u_min) == (udim - 1001) % 10 and int(v_min) == (udim - 1001) // 10:
                        uv_bboxes.append((u_min, u_max, v_min, v_max, mesh, material, face_id))
            
            except Exception as e:
                print(f"Error processing mesh {mesh}: {str(e)}")
        
        # Check for overlaps within the UDIM
        tolerance = 0.0001
        for i, (u_min1, u_max1, v_min1, v_max1, mesh1, material1, face_id1) in enumerate(uv_bboxes):
            for j, (u_min2, u_max2, v_min2, v_max2, mesh2, material2, face_id2) in enumerate(uv_bboxes[i+1:], i+1):
                if (u_min1 < u_max2 - tolerance and u_max1 > u_min2 + tolerance and
                    v_min1 < v_max2 - tolerance and v_max1 > v_min2 + tolerance):
                    if mesh1 != mesh2 or (mesh1 == mesh2 and face_id1 != face_id2):
                        # Ensure we only report each overlap once
                        overlap_pair = tuple(sorted([f"{mesh1}_{face_id1}", f"{mesh2}_{face_id2}"]))
                        if overlap_pair not in reported_overlaps:
                            overlap_info[udim][mesh1].add((mesh2, material1, material2))
                            if mesh1 != mesh2:
                                overlap_info[udim][mesh2].add((mesh1, material2, material1))
                            reported_overlaps.add(overlap_pair)
    
    return overlap_info

def update_ui_content():
    # Clear existing content
    children = cmds.layout('contentColumn', query=True, childArray=True) or []
    for child in children:
        cmds.deleteUI(child)

    # Create progress bar and status text
    cmds.progressBar('progressBar', parent='contentColumn', maxValue=100, width=380)
    cmds.text('statusText', parent='contentColumn', label="", align='center')

    def update_progress(value, status):
        cmds.progressBar('progressBar', edit=True, progress=value)
        cmds.text('statusText', edit=True, label=status)
        cmds.refresh()

    def process_materials():
        try:
            update_progress(0, "Processing materials...")
            material_udim_map = get_materials_udim_map()
            update_progress(33, "Identifying shared UDIMs...")
            shared_udims = identify_shared_udims(material_udim_map)
            update_progress(66, "Checking UV overlap...")
            overlap_info = check_uv_overlap(material_udim_map)
            update_progress(90, "Generating UI...")
            
            if not material_udim_map:
                cmds.text(parent='contentColumn', label="No materials with UVs found.", align='center', font='boldLabelFont')
            else:
                materials_frame = cmds.frameLayout(parent='contentColumn', label="Materials and their UDIMs", collapsable=True, collapse=True, marginHeight=10, marginWidth=10)
                materials_column = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, parent=materials_frame)
                
                for material, udims in material_udim_map.items():
                    cmds.text(label=f"Material: {material}", align='left', font='boldLabelFont', backgroundColor=(0.2, 0.2, 0.2), height=25)
                    for udim in udims:
                        cmds.text(label=f"  UDIM: {udim}", align='left', backgroundColor=(0.3, 0.3, 0.3))

                shared_udims_frame = cmds.frameLayout(parent='contentColumn', label="Shared UDIMs", collapsable=True, collapse=False, marginHeight=10, marginWidth=10)
                shared_udims_column = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, parent=shared_udims_frame)

                if shared_udims:
                    for udim, materials in shared_udims.items():
                        cmds.text(label=f"UDIM {udim} is shared by:", align='left', font='boldLabelFont', backgroundColor=(0.5, 0.0, 0.0))
                        for material in materials:
                            cmds.text(label=f"  Material: {material}", align='left', backgroundColor=(0.6, 0.2, 0.2))
                else:
                    cmds.text(label="No shared UDIMs found.", align='center', font='boldLabelFont', backgroundColor=(0.0, 0.5, 0.0))

                uv_overlap_frame = cmds.frameLayout(parent='contentColumn', label="UV Overlap", collapsable=True, collapse=False, marginHeight=10, marginWidth=10)
                uv_overlap_column = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, parent=uv_overlap_frame)

                if overlap_info:
                    cmds.text(label="Meshes with overlapping UVs:", align='left', font='boldLabelFont', backgroundColor=(0.5, 0.0, 0.0))
                    for udim, mesh_overlaps in overlap_info.items():
                        cmds.text(label=f"UDIM {udim}:", align='left', font='boldLabelFont', backgroundColor=(0.4, 0.0, 0.0))
                        reported_pairs = set()
                        for mesh, overlaps in mesh_overlaps.items():
                            short_name = mesh.split("|")[-1]
                            for overlap_mesh, material1, material2 in overlaps:
                                overlap_short_name = overlap_mesh.split("|")[-1]
                                pair = tuple(sorted([short_name, overlap_short_name]))
                                if pair not in reported_pairs:
                                    if short_name == overlap_short_name:
                                        cmds.text(label=f"  {short_name} ({material1}) has self-overlapping UVs", align='left', backgroundColor=(0.6, 0.2, 0.2))
                                    else:
                                        cmds.text(label=f"  {short_name} ({material1}) overlaps with {overlap_short_name} ({material2})", align='left', backgroundColor=(0.6, 0.2, 0.2))
                                    reported_pairs.add(pair)
                else:
                    cmds.text(label="No UV overlaps found.", align='center', font='boldLabelFont', backgroundColor=(0.0, 0.5, 0.0))

            update_progress(100, "Completed!")
        except Exception as e:
            cmds.text(parent='contentColumn', label=f"An error occurred: {str(e)}", align='center', font='boldLabelFont')

    cmds.scriptJob(parent='udimWindow', runOnce=True, event=["idle", process_materials])

def refresh_ui(*args):
    update_ui_content()

def create_udim_ui():
    if cmds.window("udimWindow", exists=True):
        cmds.deleteUI("udimWindow")

    window = cmds.window("udimWindow", title="UDIM Analysis Tool", widthHeight=(400, 600))
    
    main_layout = cmds.columnLayout('mainColumn', adjustableColumn=True, rowSpacing=10)
    
    # Create the refresh button at the top
    cmds.button(parent=main_layout, label='Refresh', command=refresh_ui, height=30, backgroundColor=(0.4, 0.4, 0.4))
    
    # Create a scroll layout for the content
    scroll_layout = cmds.scrollLayout(parent=main_layout, childResizable=True, height=570)
    
    # Create a column layout for the content that will be updated
    content_layout = cmds.columnLayout('contentColumn', adjustableColumn=True, rowSpacing=10, parent=scroll_layout)

    update_ui_content()

    cmds.showWindow(window)

# Run the function to create the UI
create_udim_ui()