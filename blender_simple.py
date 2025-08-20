import bpy
import bmesh
import mathutils
import os
import math
from bpy.props import StringProperty, EnumProperty, IntProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras.io_utils import ImportHelper

class BlenderExporter:
    def __init__(self):
        self.setup_scene()
        
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
        
        # Set white world color
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
        
        # Analyze all animation frames for dynamic camera
        if animation_name:
            center, size = self.analyze_animation_bounds(target_object, animation_name, padding_enabled, padding_percent)
        else:
            bbox = [target_object.matrix_world @ mathutils.Vector(corner) for corner in target_object.bound_box]
            min_coords = [min([v[i] for v in bbox]) for i in range(3)]
            max_coords = [max([v[i] for v in bbox]) for i in range(3)]
            center = mathutils.Vector([(min_coords[i] + max_coords[i]) / 2 for i in range(3)])
            size = max(max_coords[i] - min_coords[i] for i in range(3))
            if padding_enabled:
                size *= (1 + padding_percent / 100)
        
        distance = size * 2.5
        
        if angle_type == "Front":
            camera.location = (center.x, center.y - distance, center.z)
        elif angle_type == "Isometric":
            camera.location = (center.x + distance * 0.7, center.y - distance * 0.7, center.z + distance * 0.7)
        elif angle_type == "Side":
            camera.location = (center.x + distance, center.y, center.z)
            
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
                               frame_count=16, camera_angle="Front", flip_animation=False, export_format='PNG'):
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
            
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        total_frames = frame_end - frame_start + 1
        
        if frame_count > total_frames:
            frame_count = total_frames
            
        frame_step = max(1, total_frames // frame_count)
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i in range(frame_count):
            frame_num = frame_start + (i * frame_step)
            bpy.context.scene.frame_set(frame_num)
            
            # Clean filename - remove invalid characters
            clean_name = animation_name.replace('|', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('<', '_').replace('>', '_').replace('"', '_')
            file_ext = '.png' if not hasattr(self, 'export_format') else ('.png' if self.export_format == 'PNG' else '.webp')
            frame_path = os.path.join(output_dir, f"{clean_name}_frame_{i:04d}{file_ext}")
            
            # Set render format
            original_format = bpy.context.scene.render.image_settings.file_format
            bpy.context.scene.render.image_settings.file_format = getattr(self, 'export_format', 'PNG')
            
            bpy.context.scene.render.filepath = frame_path
            bpy.ops.render.render(write_still=True)
            
            # Restore original format
            bpy.context.scene.render.image_settings.file_format = original_format
            
        return frame_count
    
    def analyze_animation_bounds(self, target_object, animation_name, padding_enabled=True, padding_percent=20):
        """Analyzes all animation frames to find maximum dimensions"""
        action = bpy.data.actions.get(animation_name)
        if not action:
            return self.get_static_bounds(target_object)
        
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        
        all_min_coords = [float('inf')] * 3
        all_max_coords = [float('-inf')] * 3
        
        # Process every 5th frame for optimization
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
        """Gets static dimensions of the object"""
        bbox = [target_object.matrix_world @ mathutils.Vector(corner) for corner in target_object.bound_box]
        min_coords = [min([v[i] for v in bbox]) for i in range(3)]
        max_coords = [max([v[i] for v in bbox]) for i in range(3)]
        center = mathutils.Vector([(min_coords[i] + max_coords[i]) / 2 for i in range(3)])
        size = max(max_coords[i] - min_coords[i] for i in range(3))
        return center, size

class AnimationExporterProperties(PropertyGroup):
    frame_size: EnumProperty(
        name="Frame Size",
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
    
    frame_count: IntProperty(
        name="Frame Count",
        default=1,
        min=1
    )
    
    camera_angle: EnumProperty(
        name="Camera Angle",
        items=[
            ('FRONT', "Front", ""),
            ('ISO', "Isometric", ""),
            ('SIDE', "Side", "")
        ],
        default='SIDE'
    )
    
    output_path: StringProperty(
        name="Output Folder",
        subtype='DIR_PATH',
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
        description="Автоматично розраховувати сітку"
    )
    
    flip_animation: bpy.props.BoolProperty(
        name="Mirror Animation",
        default=True,
        description="Віддзеркалити анімацію горизонтально"
    )
    
    export_format: EnumProperty(
        name="Export Format",
        items=[
            ('PNG', "PNG", "Export to PNG format"),
            ('WEBP', "WEBP", "Export to WEBP format")
        ],
        default='PNG'
    )
    
    camera_padding_enabled: bpy.props.BoolProperty(
        name="Add Camera Padding",
        default=True,
        description="Add padding around the camera to prevent model clipping"
    )
    
    camera_padding_percent: IntProperty(
        name="Camera Padding (%)",
        default=20,
        min=1,
        max=100,
        description="Percentage of padding around the camera"
    )

class ANIM_OT_export_frames(Operator):
    bl_idname = "anim.export_frames"
    bl_label = "Export as Frames"
    bl_description = "Export animation as separate PNG frames"
    
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
            angle_map = {'FRONT': 'Фронтальний', 'ISO': 'Ізометричний', 'SIDE': 'Бічний'}
            
            frame_count = exporter.export_animation_frames(
                animation_name=action.name,
                output_dir=props.output_path,
                frame_size=(size, size),
                frame_count=props.frame_count,
                camera_angle=angle_map[props.camera_angle],
                flip_animation=props.flip_animation,
                export_format=props.export_format
            )
            
            self.report({'INFO'}, f"Exported {frame_count} frames to: {props.output_path}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}

class ANIM_OT_export_spritesheet(Operator):
    bl_idname = "anim.export_spritesheet"
    bl_label = "Export as SpriteSheet"
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
            angle_map = {'FRONT': 'Фронтальний', 'ISO': 'Ізометричний', 'SIDE': 'Бічний'}
            
            clean_name = action.name.replace('|', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('<', '_').replace('>', '_').replace('"', '_')
            file_ext = '.png' if props.export_format == 'PNG' else '.webp'
            output_file = os.path.join(props.output_path, f"{clean_name}_spritesheet{file_ext}")
            
            # Simple spritesheet creation
            temp_dir = os.path.join(props.output_path, "temp_frames")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Calculate grid if auto mode
            if props.auto_grid:
                import math
                cols = int(math.ceil(math.sqrt(props.frame_count)))
                rows = int(math.ceil(props.frame_count / cols))
                max_frames = props.frame_count
            else:
                cols = props.sprite_columns
                rows = props.sprite_rows
                max_frames = cols * rows
            
            frame_count = exporter.export_animation_frames(
                animation_name=action.name,
                output_dir=temp_dir,
                frame_size=(size, size),
                frame_count=min(props.frame_count, max_frames),
                camera_angle=angle_map[props.camera_angle],
                flip_animation=props.flip_animation,
                export_format=props.export_format
            )
            
            # Create spritesheet using Blender image editor
            file_ext = '.png' if props.export_format == 'PNG' else '.webp'
            # Сортуємо файли по номеру кадру для правильної послідовності
            all_files = [f for f in os.listdir(temp_dir) if f.endswith(file_ext.replace('.', ''))]
            frame_files = sorted(all_files, key=lambda x: int(x.split('_frame_')[1].split('.')[0]) if '_frame_' in x else 0)
            print(f"Found frame files: {frame_files[:5]}...")  # Показуємо перші 5
            
            if frame_files and len(frame_files) >= frame_count:
                # Create new image for spritesheet
                spritesheet_width = cols * size
                spritesheet_height = rows * size
                
                # Create blank image
                spritesheet_img = bpy.data.images.new("Spritesheet", spritesheet_width, spritesheet_height, alpha=True)
                
                # Load all frame images
                frame_images = []
                for i, frame_file in enumerate(frame_files[:frame_count]):
                    frame_path = os.path.join(temp_dir, frame_file)
                    if os.path.exists(frame_path):
                        img = bpy.data.images.load(frame_path)
                        frame_images.append(img)
                
                # Initialize spritesheet with transparent pixels
                pixels = [0.0, 0.0, 0.0, 0.0] * (spritesheet_width * spritesheet_height)
                
                # Перевіряємо послідовність кадрів
                print(f"Processing {len(frame_images)} frames for {cols}x{rows} grid")
                
                for frame_index in range(min(frame_count, len(frame_images), cols * rows)):
                    img = frame_images[frame_index]
                    
                    # Позиція в сітці: зліва направо, зверху вниз
                    col = frame_index % cols
                    row = frame_index // cols
                    
                    print(f"Frame {frame_index}: position ({col}, {row})")
                    
                    # Get frame pixels
                    frame_pixels = [0.0] * (size * size * 4)
                    img.pixels.foreach_get(frame_pixels)
                    
                    # Copy pixels to correct position in spritesheet
                    for y in range(size):
                        for x in range(size):
                            src_idx = (y * size + x) * 4
                            dst_x = col * size + x
                            dst_y = row * size + y
                            dst_idx = (dst_y * spritesheet_width + dst_x) * 4
                            
                            if dst_idx + 3 < len(pixels) and src_idx + 3 < len(frame_pixels):
                                pixels[dst_idx] = frame_pixels[src_idx]      # R
                                pixels[dst_idx+1] = frame_pixels[src_idx+1]  # G
                                pixels[dst_idx+2] = frame_pixels[src_idx+2]  # B
                                pixels[dst_idx+3] = frame_pixels[src_idx+3]  # A
                
                # Set pixels to spritesheet
                spritesheet_img.pixels.foreach_set(pixels)
                spritesheet_img.update()
                
                # Save spritesheet in selected format
                spritesheet_img.filepath_raw = output_file
                if props.export_format == 'WEBP':
                    spritesheet_img.file_format = 'WEBP'
                else:
                    spritesheet_img.file_format = 'PNG'
                spritesheet_img.save()
                
                # Clean up loaded images
                for img in frame_images:
                    bpy.data.images.remove(img)
                bpy.data.images.remove(spritesheet_img)
            
            # Cleanup temp files
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            if props.auto_grid:
                self.report({'INFO'}, f"Exported spritesheet: {output_file} ({cols}x{rows})")
            else:
                self.report({'INFO'}, f"Exported spritesheet: {output_file} ({props.sprite_columns}x{props.sprite_rows})")
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
            # Clear the scene and cache before import
            self.clear_scene_and_cache()
            
            # Обробка множинних файлів (для drag and drop)
            if self.files:
                import_dir = os.path.dirname(self.filepath)
                for file_elem in self.files:
                    filepath = os.path.join(import_dir, file_elem.name)
                    self.import_single_file(filepath)
            else:
                self.import_single_file(self.filepath)
                
            self.setup_imported_objects()
            self.set_animation_frame_count(context)
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
    
    def setup_imported_objects(self):
        # Нормалізуємо scale тільки для об'єктів менших за 1.0
        for obj in bpy.data.objects:
            if obj.type in ['MESH', 'ARMATURE']:
                new_scale = [
                    max(obj.scale[0], 1.0) if obj.scale[0] < 1.0 else obj.scale[0],
                    max(obj.scale[1], 1.0) if obj.scale[1] < 1.0 else obj.scale[1],
                    max(obj.scale[2], 1.0) if obj.scale[2] < 1.0 else obj.scale[2]
                ]
                obj.scale = new_scale
                
        # Встановлюємо вид збоку (-X)
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        bpy.ops.view3d.view_axis(type='LEFT')
                        break
                break
                
        # Налаштовуємо матеріали
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
                
                nodes_to_remove = []
                for node in nodes:
                    if node.type in ['NORMAL_MAP', 'BUMP']:
                        nodes_to_remove.append(node)
                
                for node in nodes_to_remove:
                    nodes.remove(node)
    
    def set_animation_frame_count(self, context):
        """Автоматично встановлює кількість кадрів на основі анімації"""
        if bpy.data.actions:
            action = bpy.data.actions[0]  # Беремо першу анімацію
            frame_start = int(action.frame_range[0])
            frame_end = int(action.frame_range[1])
            total_frames = frame_end - frame_start + 1
            context.scene.anim_exporter.frame_count = total_frames
    
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

class ANIM_PT_exporter_panel(Panel):
    bl_label = "3D to 2D Animation Exporter"
    bl_idname = "ANIM_PT_exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Animation"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.anim_exporter
        
        box = layout.box()
        box.label(text="Animation Import:")
        
        box.operator("anim.import_model", text="Import FBX/GLB", icon='IMPORT')
            
        box = layout.box()
        box.label(text="Export Settings:")
        box.prop(props, "frame_size")
        box.prop(props, "frame_count")
        box.prop(props, "camera_angle")
        box.prop(props, "flip_animation")
        box.prop(props, "camera_padding_enabled")
        if props.camera_padding_enabled:
            box.prop(props, "camera_padding_percent")
        box.prop(props, "export_format")
        box.prop(props, "output_path")
        
        box = layout.box()
        box.label(text="Sprite Sheet Settings:")
        box.prop(props, "auto_grid")
        
        row = box.row()
        row.enabled = not props.auto_grid
        row.prop(props, "sprite_columns")
        row.prop(props, "sprite_rows")
        
        layout.separator()
        row = layout.row()
        row.operator("anim.export_frames", text="Export as Frames", icon='RENDER_ANIMATION')
        row.operator("anim.export_spritesheet", text="Export as SpriteSheet", icon='TEXTURE')

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

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.anim_exporter

if __name__ == "__main__":
    # Clear the scene when starting the program
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    register()
    print("3D to 2D Animation Exporter (Simple) loaded!")