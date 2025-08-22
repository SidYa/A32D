import bpy
import bmesh
import mathutils
import os
import math
from bpy.props import StringProperty, EnumProperty, IntProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras.io_utils import ImportHelper
try:
	from PIL import Image as _PILImage
	_PIL_AVAILABLE = True
except Exception:
	_PIL_AVAILABLE = False

# --- Live camera preview helpers ---
def refresh_camera_preview(context):
    """Recreate/position camera based on current properties for live preview."""
    try:
        props = context.scene.anim_exporter
    except Exception:
        return
    if not props:
        return
    exporter = BlenderExporter()
    target = exporter.find_target_object()
    if not target:
        return
    angle_map = {'FRONT': 'Front', 'ISO': 'Isometric', 'SIDE': 'Side', 'CUSTOM': 'Custom'}
    # Use current action to compute animation bounds like export does
    action_name = None
    if bpy.data.actions:
        action_name = bpy.data.actions[0].name
    if context.object and context.object.animation_data and context.object.animation_data.action:
        action_name = context.object.animation_data.action.name

    exporter.setup_camera(
        target,
        angle_type=angle_map.get(props.camera_angle, 'Side'),
        animation_name=action_name,
        padding_enabled=props.camera_padding_enabled,
        padding_percent=props.camera_padding_percent
    )
    exporter.setup_flip_modifier(props.flip_animation, target, angle_map.get(props.camera_angle, 'Side'))
    # Ensure square preview to match export output
    try:
        size_val = int(props.frame_size)
    except Exception:
        size_val = 512
    bpy.context.scene.render.resolution_x = size_val
    bpy.context.scene.render.resolution_y = size_val

def on_camera_prop_update(self, context):
    """Update callback for camera-related properties to refresh preview."""
    refresh_camera_preview(context)

def _set_3dview_left_ortho_and_show_sidebar():
    """Set the first 3D View to LEFT with a proper override (like clicking -X).
    Also activate the A32D sidebar tab using the correct 'active_panel_category' attribute.
    Returns True if both view and tab are set successfully.
    """
    try:
        screen = bpy.context.screen
        if not screen:
            return False
        view_ok = False
        tab_ok = False
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            # Ensure the sidebar (N-panel) is visible for this area
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.show_region_ui = True
                    break
            win_region = None
            ui_region = None
            for region in area.regions:
                if region.type == 'WINDOW':
                    win_region = region
                elif region.type == 'UI':
                    ui_region = region
            if win_region:
                try:
                    with bpy.context.temp_override(window=bpy.context.window, area=area, region=win_region):
                        bpy.ops.view3d.view_axis(type='LEFT')
                        if bpy.context.space_data and getattr(bpy.context.space_data, 'region_3d', None):
                            bpy.context.space_data.region_3d.view_perspective = 'ORTHO'
                        view_ok = True
                except Exception:
                    view_ok = False
            if ui_region:
                # Set active sidebar category using the correct attribute
                try:
                    if hasattr(ui_region, 'active_panel_category'):
                        setattr(ui_region, 'active_panel_category', 'A32D')
                        tab_ok = True
                except Exception:
                    tab_ok = False
        return bool(view_ok and tab_ok)
    except Exception:
        return False

def _remove_default_collection_child_on_start():
    """Flatten any default child 'Collection' under the Scene Collection and remove it if emptyable."""
    try:
        scene = bpy.context.scene
        if not scene:
            return
        master = scene.collection
        # Move contents of any child named 'Collection' directly to master, then remove that child
        for child in list(master.children):
            if child.name == 'Collection':
                # Move objects
                for obj in list(child.objects):
                    if obj.name not in master.objects:
                        master.objects.link(obj)
                    try:
                        child.objects.unlink(obj)
                    except Exception:
                        pass
                # Move sub-collections
                for sub in list(child.children):
                    if sub not in master.children:
                        master.children.link(sub)
                    try:
                        child.children.unlink(sub)
                    except Exception:
                        pass
                # Unlink and remove the emptied child
                try:
                    master.children.unlink(child)
                except Exception:
                    pass
                try:
                    bpy.data.collections.remove(child)
                except Exception:
                    pass
    except Exception:
        pass

def _setup_workspace_tabs():
    """Remove unnecessary workspace tabs, keep only Layout, UV Editing, Texture Paint, Shading, Animation"""
    try:
        required_tabs = {'Layout', 'UV Editing', 'Texture Paint', 'Shading', 'Animation'}
        
        # Switch to Layout first to avoid deleting active workspace
        layout_ws = bpy.data.workspaces.get('Layout')
        if layout_ws:
            bpy.context.window.workspace = layout_ws
        
        # Remove unwanted workspaces
        workspaces_to_remove = [ws for ws in bpy.data.workspaces if ws.name not in required_tabs]
        
        for workspace in workspaces_to_remove:
            try:
                bpy.data.batch_remove(ids=[workspace])
            except Exception:
                pass
                
        return True
    except Exception:
        return False

def _startup_setup_once():
    """Timer callback to apply initial viewport and collection cleanup after Blender opens.
    Retries until Left Ortho and A32D tab are both set.
    """
    try:
        done = _set_3dview_left_ortho_and_show_sidebar()
        _remove_default_collection_child_on_start()
        _setup_workspace_tabs()
        
        # Hide system console at the end
        if done:
            try:
                bpy.ops.wm.console_toggle()
            except Exception:
                pass
        
        return None if done else 0.5
    except Exception:
        return 0.5

class BlenderExporter:
    def __init__(self):
        self.setup_scene()
    
    def _move_object_to_scene_root(self, obj):
        try:
            scene = bpy.context.scene
            if not scene or not obj:
                return
            master = scene.collection
            # Link to master if not already
            if obj.name not in master.objects:
                master.objects.link(obj)
            # Unlink from all other collections
            for coll in list(obj.users_collection):
                if coll is not master:
                    try:
                        coll.objects.unlink(obj)
                    except Exception:
                        pass
        except Exception:
            pass
        
    def setup_scene(self):
        bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
        bpy.context.scene.render.film_transparent = True
        self.setup_lighting()
        
    def setup_lighting(self):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT':
                obj.select_set(True)
        bpy.ops.object.delete()
        
        bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
        sun = bpy.context.active_object
        sun.data.energy = 3
        sun.data.color = (1.0, 1.0, 1.0)  # White color #FFFFFF
        # Ensure sun is in Scene Collection root
        self._move_object_to_scene_root(sun)
        
        # Set world background to white
        if bpy.context.scene.world:
            bpy.context.scene.world.use_nodes = True
            world_nodes = bpy.context.scene.world.node_tree.nodes
            bg_node = world_nodes.get('Background')
            if bg_node:
                bg_node.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)  # White color #FFFFFF
        
    def setup_camera(self, target_object, angle_type="Front", animation_name=None, padding_enabled=True, padding_percent=20):
        if bpy.data.objects.get("Camera"):
            bpy.data.objects.remove(bpy.data.objects["Camera"])
            
        bpy.ops.object.camera_add()
        camera = bpy.context.active_object
        # Ensure camera is in Scene Collection root
        self._move_object_to_scene_root(camera)
        
        # Use static object bounds for consistent scale across all animations
        center, size = self.get_static_bounds(target_object)
        if padding_enabled:
            size *= (1 + padding_percent / 100)
        
        distance = size * 2.5
        
        if angle_type == "Front":
            camera.location = (center.x, center.y - distance, center.z)
        elif angle_type == "Isometric":
            camera.location = (center.x + distance * 0.7, center.y - distance * 0.7, center.z + distance * 0.7)
        elif angle_type == "Side":
            camera.location = (center.x + distance, center.y, center.z)
        elif angle_type == "Custom":
            # Position and rotate based on custom orientation
            props = bpy.context.scene.anim_exporter
            orientation = getattr(props, 'custom_orientation', 'SIDE')
            angle_deg = getattr(props, 'custom_camera_deg', 0)
            if orientation == 'SIDE':
                base_loc = mathutils.Vector((center.x + distance, center.y, center.z))
                axis = 'Z'  # orbit horizontally around vertical axis
            elif orientation == 'UP':
                base_loc = mathutils.Vector((center.x, center.y, center.z + distance))
                axis = 'X'  # orbit vertically from top view
            else:  # 'DOWN'
                base_loc = mathutils.Vector((center.x, center.y, center.z - distance))
                axis = 'X'  # orbit vertically from bottom view
            angle_rad = math.radians(angle_deg)
            rot_mat = mathutils.Matrix.Rotation(angle_rad, 4, axis)
            offset = base_loc - center
            rotated = rot_mat @ offset
            new_loc = center + rotated
            camera.location = (new_loc.x, new_loc.y, new_loc.z)
            
        direction = center - camera.location
        camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = size * 1.2
        bpy.context.scene.camera = camera
        
    def setup_flip_modifier(self, flip_enabled, target_object, angle_type):
        """Setup camera flip by moving to opposite side"""
        if flip_enabled:
            camera = bpy.context.scene.camera
            if camera:
                # Get model center
                bbox = [target_object.matrix_world @ mathutils.Vector(corner) for corner in target_object.bound_box]
                min_coords = [min([v[i] for v in bbox]) for i in range(3)]
                max_coords = [max([v[i] for v in bbox]) for i in range(3)]
                center = mathutils.Vector([(min_coords[i] + max_coords[i]) / 2 for i in range(3)])
                
                # Flip camera position horizontally around model center
                if angle_type == "Front":
                    # Move camera to back instead of front
                    size = max(max_coords[i] - min_coords[i] for i in range(3))
                    distance = size * 2.5
                    camera.location = (center.x, center.y + distance, center.z)
                elif angle_type == "Isometric":
                    # Flip isometric position
                    size = max(max_coords[i] - min_coords[i] for i in range(3))
                    distance = size * 2.5
                    camera.location = (center.x - distance * 0.7, center.y + distance * 0.7, center.z + distance * 0.7)
                elif angle_type == "Side":
                    # Move to opposite side
                    size = max(max_coords[i] - min_coords[i] for i in range(3))
                    distance = size * 2.5
                    camera.location = (center.x - distance, center.y, center.z)
                elif angle_type == "Custom":
                    # Mirror current camera position around the model center to preserve custom orientation
                    offset = camera.location - center
                    camera.location = center - offset
                
                # Reorient camera to look at center
                direction = center - camera.location
                camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        
    def find_target_object(self):
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                return obj
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and len(obj.data.vertices) > 0:
                return obj
        return None
        
    def export_animation_frames(self, animation_name, output_dir, frame_size=(128, 128), 
                               start_frame=None, end_frame=None, camera_angle="Front", flip_animation=False, export_format='PNG', base_name_override=None):
        self.export_format = export_format
        target_obj = self.find_target_object()
        if not target_obj:
            raise Exception("No objects found")
            
        props = bpy.context.scene.anim_exporter
        self.setup_camera(target_obj, camera_angle, animation_name, props.camera_padding_enabled, props.camera_padding_percent)
        self.setup_flip_modifier(flip_animation, target_obj, camera_angle)
        
        bpy.context.scene.render.resolution_x = frame_size[0]
        bpy.context.scene.render.resolution_y = frame_size[1]
        
        action = bpy.data.actions.get(animation_name)
        if not action:
            raise Exception(f"Animation '{animation_name}' not found")
            
        if target_obj.type == 'ARMATURE':
            target_obj.animation_data_create()
            target_obj.animation_data.action = action
            
        action_start = int(action.frame_range[0])
        action_end = int(action.frame_range[1])
        if start_frame is None:
            start_frame = action_start
        if end_frame is None:
            end_frame = action_end
        start_frame = max(action_start, int(start_frame))
        end_frame = min(action_end, int(end_frame))
        if start_frame > end_frame:
            start_frame, end_frame = end_frame, start_frame
        frames_to_export = list(range(start_frame, end_frame + 1))
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i, frame_num in enumerate(frames_to_export):
            bpy.context.scene.frame_set(frame_num)
            
            # Clean filename - remove invalid characters
            name_source = base_name_override if base_name_override else animation_name
            clean_name = name_source.replace('|', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('<', '_').replace('>', '_').replace('"', '_')
            file_ext = '.png' if not hasattr(self, 'export_format') else ('.png' if self.export_format == 'PNG' else '.webp')
            frame_path = os.path.join(output_dir, f"{clean_name}_frame_{i:04d}{file_ext}")
            
            # Set render format
            original_format = bpy.context.scene.render.image_settings.file_format
            bpy.context.scene.render.image_settings.file_format = getattr(self, 'export_format', 'PNG')
            
            bpy.context.scene.render.filepath = frame_path
            bpy.ops.render.render(write_still=True)
            
            # Restore original format
            bpy.context.scene.render.image_settings.file_format = original_format
            
        return len(frames_to_export)
    
    def analyze_animation_bounds(self, target_object, animation_name, padding_enabled=True, padding_percent=20):
        """Analyze all animation frames to find maximum bounds"""
        action = bpy.data.actions.get(animation_name)
        if not action:
            return self.get_static_bounds(target_object)
        
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        
        all_min_coords = [float('inf')] * 3
        all_max_coords = [float('-inf')] * 3
        
        # Iterate every Nth frame for optimization
        step = max(1, (frame_end - frame_start) // 20)
        for frame in range(frame_start, frame_end + 1, step):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            
            bbox = [target_object.matrix_world @ mathutils.Vector(corner) for corner in target_object.bound_box]
            frame_min = [min([v[i] for v in bbox]) for i in range(3)]
            frame_max = [max([v[i] for v in bbox]) for i in range(3)]
            
            for i in range(3):
                all_min_coords[i] = min(all_min_coords[i], frame_min[i])
                all_max_coords[i] = max(all_max_coords[i], frame_max[i])
        
        center = mathutils.Vector([(all_min_coords[i] + all_max_coords[i]) / 2 for i in range(3)])
        size = max(all_max_coords[i] - all_min_coords[i] for i in range(3))
        
        if padding_enabled:
            size *= (1 + padding_percent / 100)
        
        return center, size
    
    def get_static_bounds(self, target_object):
        """Get static object bounds"""
        bbox = [target_object.matrix_world @ mathutils.Vector(corner) for corner in target_object.bound_box]
        min_coords = [min([v[i] for v in bbox]) for i in range(3)]
        max_coords = [max([v[i] for v in bbox]) for i in range(3)]
        center = mathutils.Vector([(min_coords[i] + max_coords[i]) / 2 for i in range(3)])
        size = max(max_coords[i] - min_coords[i] for i in range(3))
        return center, size

class AnimationExporterProperties(PropertyGroup):
    frame_size: EnumProperty(
        name="Size",
        items=[
            ('64', "64x64", ""),
            ('128', "128x128", ""),
            ('256', "256x256", ""),
            ('512', "512x512", ""),
            ('1024', "1024x1024", ""),
            ('2048', "2048x2048", "")
        ],
        default='512'
    )
    
    start_frame: IntProperty(
        name="Start:",
        default=1,
        min=1
    )

    end_frame: IntProperty(
        name="End:",
        default=1,
        min=1
    )
    
    camera_angle: EnumProperty(
        name="Angle",
        items=[
            ('FRONT', "Front", ""),
            ('ISO', "Isometric", ""),
            ('SIDE', "Side", ""),
            ('CUSTOM', "Custom", "Use custom X tilt")
        ],
        default='SIDE',
        update=on_camera_prop_update
    )
    
    output_path: StringProperty(
        name="Folder",
        subtype='DIR_PATH',
        default=""
    )
    
    # Preferred base name for exported files (set on import from file name)
    export_basename: StringProperty(
        name="Export Name",
        default=""
    )
    
    sprite_columns: IntProperty(
        name="Columns",
        default=4,
        min=1,
        max=20
    )
    
    sprite_rows: IntProperty(
        name="Rows",
        default=4,
        min=1,
        max=20
    )
    
    auto_grid: bpy.props.BoolProperty(
        name="Auto",
        default=True,
        description="Automatically calculate grid"
    )
    
    flip_animation: bpy.props.BoolProperty(
        name="Flip Camera",
        default=True,
        description="Flip animation horizontally",
        update=on_camera_prop_update
    )
    
    export_format: EnumProperty(
        name="Format",
        items=[
            ('PNG', "PNG", "Export in PNG format"),
            ('WEBP', "WEBP", "Export in WEBP format")
        ],
        default='PNG'
    )
    
    camera_padding_enabled: bpy.props.BoolProperty(
        name="Add Camera Padding",
        default=False,
        description="Add padding so the model isn't clipped",
        update=on_camera_prop_update
    )
    
    camera_padding_percent: IntProperty(
        name="Camera Padding (%)",
        default=20,
        min=1,
        max=100,
        description="Padding percentage for camera",
        update=on_camera_prop_update
    )

    # Custom camera controls (visible only when camera_angle == 'CUSTOM')
    custom_orientation: EnumProperty(
        name="Custom Orientation",
        items=[
            ('SIDE', "Side", "Orbit horizontally (around Z) from side view"),
            ('UP', "Up", "Orbit vertically (around X) from top view")
        ],
        default='SIDE',
        update=on_camera_prop_update
    )
    custom_camera_deg: IntProperty(
        name="Custom Angle (deg)",
        default=0,
        min=-180,
        max=180,
        description="Rotation angle for Custom orientation",
        update=on_camera_prop_update
    )



class ANIM_OT_export_frames(Operator):
    bl_idname = "anim.export_frames"
    bl_label = "Sprites"
    bl_description = "Export animation as separate sprite images"
    
    def execute(self, context):
        props = context.scene.anim_exporter
        
        if not bpy.data.actions:
            self.report({'ERROR'}, "No animations found")
            return {'CANCELLED'}
            
        if not props.output_path:
            self.report({'ERROR'}, "Please set output path")
            return {'CANCELLED'}
            
        try:
            exporter = BlenderExporter()
            
            action = None
            if context.object and context.object.animation_data:
                action = context.object.animation_data.action
            if not action and bpy.data.actions:
                action = bpy.data.actions[0]
                
            if not action:
                self.report({'ERROR'}, "No animation selected")
                return {'CANCELLED'}
                
            size = int(props.frame_size)
            angle_map = {'FRONT': 'Front', 'ISO': 'Isometric', 'SIDE': 'Side', 'CUSTOM': 'Custom'}
            
            # Choose export base name for frames
            base_name = getattr(props, 'export_basename', '').strip()
            chosen_name = base_name if base_name else action.name
            
            frame_count = exporter.export_animation_frames(
                animation_name=action.name,
                output_dir=props.output_path,
                frame_size=(size, size),
                start_frame=props.start_frame,
                end_frame=props.end_frame,
                camera_angle=angle_map[props.camera_angle],
                flip_animation=props.flip_animation,
                export_format=props.export_format,
                base_name_override=chosen_name
            )
            
            self.report({'INFO'}, f"Exported {frame_count} frames to: {props.output_path}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}

class ANIM_OT_export_spritesheet(Operator):
    bl_idname = "anim.export_spritesheet"
    bl_label = "Spritesheet"
    bl_description = "Export animation as spritesheet"
    
    def execute(self, context):
        props = context.scene.anim_exporter
        
        if not bpy.data.actions:
            self.report({'ERROR'}, "No animations found")
            return {'CANCELLED'}
            
        if not props.output_path:
            self.report({'ERROR'}, "Please set output path")
            return {'CANCELLED'}
            
        try:
            exporter = BlenderExporter()
            
            action = None
            if context.object and context.object.animation_data:
                action = context.object.animation_data.action
            if not action and bpy.data.actions:
                action = bpy.data.actions[0]
                
            if not action:
                self.report({'ERROR'}, "No animation selected")
                return {'CANCELLED'}
                
            size = int(props.frame_size)
            angle_map = {'FRONT': 'Front', 'ISO': 'Isometric', 'SIDE': 'Side', 'CUSTOM': 'Custom'}
            
            # Choose export name: prefer file base name captured on import, fallback to action name
            base_name = getattr(props, 'export_basename', '').strip()
            chosen_name = base_name if base_name else action.name
            clean_name = chosen_name.replace('|', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('<', '_').replace('>', '_').replace('"', '_')
            file_ext = '.png' if props.export_format == 'PNG' else '.webp'
            
            # Simple spritesheet creation
            temp_dir = os.path.join(props.output_path, "temp_frames")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Auto-calc grid like GUI: square-ish (cols ~ sqrt(n), rows = ceil(n/cols))
            import math
            # derive desired frame count from range
            action_start = int(action.frame_range[0])
            action_end = int(action.frame_range[1])
            start_f = max(action_start, int(props.start_frame))
            end_f = min(action_end, int(props.end_frame))
            if start_f > end_f:
                start_f, end_f = end_f, start_f
            desired_frames = end_f - start_f + 1
            cols = int(math.ceil(math.sqrt(desired_frames)))
            rows = int(math.ceil(desired_frames / cols))
            max_frames = cols * rows
            
            export_count = min(desired_frames, max_frames)
            end_export = start_f + export_count - 1
            frame_count = exporter.export_animation_frames(
                animation_name=action.name,
                output_dir=temp_dir,
                frame_size=(size, size),
                start_frame=start_f,
                end_frame=end_export,
                camera_angle=angle_map[props.camera_angle],
                flip_animation=props.flip_animation,
                export_format=props.export_format
            )
            
            # Create spritesheet using GUI logic (PIL if available), fallback to Blender image API
            file_ext = '.png' if props.export_format == 'PNG' else '.webp'
            # Sort files by frame number for correct order
            all_files = [f for f in os.listdir(temp_dir) if f.lower().endswith(file_ext)]
            frame_files = sorted(all_files, key=lambda x: int(x.split('_frame_')[1].split('.')[0]) if '_frame_' in x else 0)

            output_file = os.path.join(props.output_path, f"{clean_name}_sh_{rows}x{cols}{file_ext}")

            if frame_files and len(frame_files) >= frame_count:
                spritesheet_width = cols * size
                spritesheet_height = rows * size

                if _PIL_AVAILABLE:
                    # PIL-based spritesheet creation
                    sheet = _PILImage.new('RGBA', (spritesheet_width, spritesheet_height))
                    for i, frame_file in enumerate(frame_files[:frame_count]):
                        frame_path = os.path.join(temp_dir, frame_file)
                        try:
                            img = _PILImage.open(frame_path).convert('RGBA')
                        except Exception:
                            continue
                        col = i % cols
                        row = i // cols
                        x_offset = col * size
                        y_offset = row * size
                        sheet.paste(img, (x_offset, y_offset))
                    # Save with correct format
                    if props.export_format == 'WEBP':
                        sheet.save(output_file, 'WEBP')
                    else:
                        sheet.save(output_file, 'PNG')
                else:
                    # Fallback: Blender image API
                    spritesheet_img = bpy.data.images.new("Spritesheet", spritesheet_width, spritesheet_height, alpha=True)
                    frame_images = []
                    for i, frame_file in enumerate(frame_files[:frame_count]):
                        frame_path = os.path.join(temp_dir, frame_file)
                        if os.path.exists(frame_path):
                            img = bpy.data.images.load(frame_path)
                            frame_images.append(img)
                    pixels = [0.0, 0.0, 0.0, 0.0] * (spritesheet_width * spritesheet_height)
                    for frame_index in range(min(frame_count, len(frame_images), cols * rows)):
                        img = frame_images[frame_index]
                        col = frame_index % cols
                        row = frame_index // cols
                        frame_pixels = [0.0] * (size * size * 4)
                        img.pixels.foreach_get(frame_pixels)
                        for y in range(size):
                            for x in range(size):
                                src_idx = (y * size + x) * 4
                                dst_x = col * size + x
                                # Place row 0 at top without flipping the frame vertically.
                                dst_y = (rows - 1 - row) * size + y
                                dst_idx = (dst_y * spritesheet_width + dst_x) * 4
                                if dst_idx + 3 < len(pixels) and src_idx + 3 < len(frame_pixels):
                                    pixels[dst_idx] = frame_pixels[src_idx]
                                    pixels[dst_idx+1] = frame_pixels[src_idx+1]
                                    pixels[dst_idx+2] = frame_pixels[src_idx+2]
                                    pixels[dst_idx+3] = frame_pixels[src_idx+3]
                    spritesheet_img.pixels.foreach_set(pixels)
                    spritesheet_img.update()
                    spritesheet_img.filepath_raw = output_file
                    spritesheet_img.file_format = 'WEBP' if props.export_format == 'WEBP' else 'PNG'
                    spritesheet_img.save()
                    for img in frame_images:
                        bpy.data.images.remove(img)
                    bpy.data.images.remove(spritesheet_img)
            
            # Cleanup temp files
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            self.report({'INFO'}, f"Exported spritesheet: {output_file} ({rows}x{cols})")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
            
    def create_spritesheet_simple_unused(self, temp_dir, output_path, frame_size, cols, rows, frame_count):
        """Create spritesheet by combining frames"""
        frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.png')])
        
        if not frame_files:
            raise Exception("No frames found")
            
        # Set render resolution for spritesheet
        original_x = bpy.context.scene.render.resolution_x
        original_y = bpy.context.scene.render.resolution_y
        
        bpy.context.scene.render.resolution_x = cols * frame_size
        bpy.context.scene.render.resolution_y = rows * frame_size
        
        # Use compositor to combine frames
        bpy.context.scene.use_nodes = True
        tree = bpy.context.scene.node_tree
        tree.nodes.clear()
        
        # Create output node
        output_node = tree.nodes.new('CompositorNodeComposite')
        output_node.location = (800, 0)
        
        # Create viewer node for background
        viewer = tree.nodes.new('CompositorNodeViewer')
        viewer.location = (600, 0)
        
        # Create alpha over node for combining
        alpha_node = tree.nodes.new('CompositorNodeAlphaOver')
        alpha_node.location = (600, 0)
        tree.links.new(alpha_node.outputs[0], output_node.inputs[0])
        
        # Load and position all frames
        for i, frame_file in enumerate(frame_files[:frame_count]):
            frame_path = os.path.join(temp_dir, frame_file)
            img = bpy.data.images.load(frame_path)
            
            # Create image node
            img_node = tree.nodes.new('CompositorNodeImage')
            img_node.image = img
            img_node.location = (i * 150, -i * 100)
            
            # Calculate position in grid
            col = i % cols
            row = i // cols
            
            # Create translate node for positioning
            translate_node = tree.nodes.new('CompositorNodeTranslate')
            translate_node.inputs[1].default_value = col * frame_size - (cols * frame_size) / 2 + frame_size / 2
            translate_node.inputs[2].default_value = (rows * frame_size) / 2 - row * frame_size - frame_size / 2
            translate_node.location = (i * 150 + 100, -i * 100)
            
            tree.links.new(img_node.outputs[0], translate_node.inputs[0])
            
            if i == 0:
                tree.links.new(translate_node.outputs[0], alpha_node.inputs[1])
            else:
                # Create new alpha over for each additional frame
                new_alpha = tree.nodes.new('CompositorNodeAlphaOver')
                new_alpha.location = (400 + i * 50, 0)
                tree.links.new(alpha_node.outputs[0], new_alpha.inputs[1])
                tree.links.new(translate_node.outputs[0], new_alpha.inputs[2])
                tree.links.new(new_alpha.outputs[0], output_node.inputs[0])
                alpha_node = new_alpha
        
        # Render the spritesheet
        bpy.context.scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        
        # Restore original resolution
        bpy.context.scene.render.resolution_x = original_x
        bpy.context.scene.render.resolution_y = original_y

# Debug operator removed per request

class ANIM_OT_import_model(Operator, ImportHelper):
    bl_idname = "anim.import_model"
    bl_label = "Import 3D Model"
    bl_description = "Import FBX or GLB model with animations"
    
    filename_ext = ""
    filter_glob: StringProperty(default="*.fbx;*.glb;*.gltf", options={'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        try:
            # Clear scene and cache before import
            self.clear_scene_and_cache()
            
            # Handle multiple files (for drag and drop)
            if self.files:
                import_dir = os.path.dirname(self.filepath)
                for file_elem in self.files:
                    filepath = os.path.join(import_dir, file_elem.name)
                    self.import_single_file(filepath)
            else:
                self.import_single_file(self.filepath)
                
            self.setup_imported_objects()
            # Remove default Collection not used by the add-on
            self.remove_default_collection()
            self.set_animation_frame_count(context)
            # Create/position camera immediately for live preview
            refresh_camera_preview(context)
            self.report({'INFO'}, f"Import completed")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            return {'CANCELLED'}
    
    def import_single_file(self, filepath):
        if filepath.lower().endswith('.fbx'):
            bpy.ops.import_scene.fbx(filepath=filepath)
        elif filepath.lower().endswith(('.glb', '.gltf')):
            bpy.ops.import_scene.gltf(filepath=filepath)
        else:
            raise Exception(f"Unsupported file format: {filepath}")
        
        # Store base name for export files
        try:
            props = bpy.context.scene.anim_exporter
            if props is not None:
                props.export_basename = os.path.splitext(os.path.basename(filepath))[0]
        except Exception:
            pass
    
    def setup_imported_objects(self):
        # Normalize scale only for objects smaller than 1.0
        for obj in bpy.data.objects:
            if obj.type in ['MESH', 'ARMATURE']:
                new_scale = [
                    max(obj.scale[0], 1.0) if obj.scale[0] < 1.0 else obj.scale[0],
                    max(obj.scale[1], 1.0) if obj.scale[1] < 1.0 else obj.scale[1],
                    max(obj.scale[2], 1.0) if obj.scale[2] < 1.0 else obj.scale[2]
                ]
                obj.scale = new_scale
        
        # Auto-focus on imported objects
        self.auto_focus_imported_objects()
                
        # Set side view (-X)
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        bpy.ops.view3d.view_axis(type='LEFT')
                        break
                break
                
        # Configure materials
        for material in bpy.data.materials:
            if material.use_nodes:
                nodes = material.node_tree.nodes
                
                principled = None
                for node in nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled = node
                        break
                
                if principled:
                    principled.inputs['Metallic'].default_value = 0.0
                    principled.inputs['Roughness'].default_value = 1.0
                    principled.inputs['IOR'].default_value = 1.2
                    
                    if principled.inputs['Alpha'].is_linked:
                        material.node_tree.links.remove(principled.inputs['Alpha'].links[0])
                    if principled.inputs['Normal'].is_linked:
                        material.node_tree.links.remove(principled.inputs['Normal'].links[0])
                    # Ensure only Base Color affects shading: robustly detach emission inputs
                    try:
                        links = material.node_tree.links
                        # Handle both legacy and newer names
                        emission_names = {"Emission", "Emission Color"}
                        strength_names = {"Emission Strength"}
                        # Detach all links going into emission-related inputs
                        for inp in principled.inputs:
                            if inp.name in emission_names or inp.name in strength_names:
                                if inp.is_linked:
                                    # remove all links targeting this input
                                    for l in list(inp.links):
                                        if l.to_node == principled and l.to_socket == inp:
                                            links.remove(l)
                                # zero defaults
                                if inp.name in emission_names:
                                    try:
                                        # color (RGB or RGBA)
                                        dv = inp.default_value
                                        if isinstance(dv, tuple) or isinstance(dv, list):
                                            # keep length
                                            zeros = [0.0] * len(dv)
                                            inp.default_value = zeros
                                        else:
                                            inp.default_value = 0.0
                                    except Exception:
                                        pass
                                if inp.name in strength_names:
                                    try:
                                        inp.default_value = 0.0
                                    except Exception:
                                        pass
                    except Exception:
                        pass
                
                nodes_to_remove = []
                for node in nodes:
                    if node.type in ['NORMAL_MAP', 'BUMP']:
                        nodes_to_remove.append(node)
                
                for node in nodes_to_remove:
                    nodes.remove(node)
    
    def remove_default_collection(self):
        """Flatten objects to Scene Collection and remove default 'Collection' child if possible."""
        try:
            scene = bpy.context.scene
            if scene is None:
                return
            master = scene.collection
            # Move contents of any child named 'Collection' directly to master, then remove that child
            default_child = None
            for child in list(master.children):
                if child.name == "Collection":
                    default_child = child
                    # Move objects
                    for obj in list(child.objects):
                        if obj.name not in master.objects:
                            master.objects.link(obj)
                        try:
                            child.objects.unlink(obj)
                        except Exception:
                            pass
                    # Move grandchildren collections to master
                    for sub in list(child.children):
                        if sub not in master.children:
                            master.children.link(sub)
                        try:
                            child.children.unlink(sub)
                        except Exception:
                            pass
                    # Unlink and remove the empty 'Collection' child
                    try:
                        master.children.unlink(child)
                    except Exception:
                        pass
                    try:
                        bpy.data.collections.remove(child)
                    except Exception:
                        pass
            # Also remove any other orphan collections named 'Collection' (not master)
            for coll in list(bpy.data.collections):
                if coll.name == "Collection" and coll is not master:
                    try:
                        bpy.data.collections.remove(coll)
                    except Exception:
                        pass
        except Exception:
            pass
    
    def set_animation_frame_count(self, context):
        """Automatically set frame range based on animation"""
        if bpy.data.actions:
            action = bpy.data.actions[0]  # Take the first animation
            frame_start = int(action.frame_range[0])
            frame_end = int(action.frame_range[1])
            context.scene.anim_exporter.start_frame = frame_start
            context.scene.anim_exporter.end_frame = frame_end
    
    def clear_scene_and_cache(self):
        # Clear all objects
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        # Clear animations
        for action in bpy.data.actions:
            bpy.data.actions.remove(action)
        
        # Clear materials
        for material in bpy.data.materials:
            bpy.data.materials.remove(material)
        
        # Clear meshes
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
        
        # Clear armatures
        for armature in bpy.data.armatures:
            bpy.data.armatures.remove(armature)
        
        # Clear images
        for image in bpy.data.images:
            if image.users == 0:
                bpy.data.images.remove(image)
    
    def auto_focus_imported_objects(self):
        """Auto-focus viewport on imported objects"""
        try:
            # Select all imported objects
            bpy.ops.object.select_all(action='DESELECT')
            for obj in bpy.data.objects:
                if obj.type in ['MESH', 'ARMATURE']:
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
            
            # Frame selected objects in viewport
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            with bpy.context.temp_override(area=area, region=region):
                                bpy.ops.view3d.view_selected()
                            break
                    break
        except Exception:
            pass

class ANIM_PT_exporter_panel(Panel):
    bl_label = "3D to 2D Animation Exporter"
    bl_idname = "ANIM_PT_exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "A32D"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.anim_exporter
        
        box = layout.box()
        box.label(text="Import Animation:")
        
        box.operator("anim.import_model", text="Import FBX/GLB", icon='IMPORT')
            
        # Frame settings block
        frame_box = layout.box()
        frame_box.label(text="Frame Settings:")
        frame_box.prop(props, "frame_size")
        row = frame_box.row()
        row.prop(props, "start_frame")
        row.prop(props, "end_frame")

        # Camera settings block
        cam_box = layout.box()
        cam_box.label(text="Camera Settings:")
        cam_box.prop(props, "camera_angle")
        if props.camera_angle == 'CUSTOM':
            cam_box.prop(props, "custom_orientation")
            cam_box.prop(props, "custom_camera_deg")
        cam_box.prop(props, "flip_animation")
        cam_box.prop(props, "camera_padding_enabled")
        if props.camera_padding_enabled:
            cam_box.prop(props, "camera_padding_percent")

        # Export block with format and output above buttons
        export_box = layout.box()
        export_box.label(text="Export:")
        export_box.prop(props, "export_format")
        export_box.prop(props, "output_path")
        row = export_box.row()
        row.operator("anim.export_frames", text="Sprites", icon='RENDER_ANIMATION')
        row.operator("anim.export_spritesheet", text="Spritesheet", icon='TEXTURE')

classes = [
    AnimationExporterProperties,
    ANIM_OT_export_frames,
    ANIM_OT_export_spritesheet,
    ANIM_OT_import_model,
    ANIM_PT_exporter_panel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.anim_exporter = bpy.props.PointerProperty(type=AnimationExporterProperties)
    # Schedule a one-shot startup setup to configure viewport and collections
    try:
        bpy.app.timers.register(_startup_setup_once, first_interval=0.5)
    except Exception:
        pass

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.anim_exporter

if __name__ == "__main__":
    # Clear scene on script start
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    register()
    print("3D to 2D Animation Exporter (Simple) loaded!")