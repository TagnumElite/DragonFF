# GTA Blender Tools - Tools to edit basic GTA formats
# Copyright (C) 2019  Parik

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import bpy
import bmesh
import mathutils
import os

from .dff import dff

#######################################################
class dff_importer:

    #######################################################
    def _init():
        self = dff_importer

        # Variables
        self.dff = None
        self.meshes = {}
        self.objects = []
        self.file_name = ""

    #######################################################
    def import_atomics():
        self = dff_importer

        # Import atomics (meshes)
        for atomic in self.dff.atomic_list:

            frame = self.dff.frame_list[atomic.frame]
            geom = self.dff.geometry_list[atomic.geometry]
            
            mesh = bpy.data.meshes.new(frame.name)
            bm   = bmesh.new()

            uv_layers = []

            # Materials
            self.import_materials(geom)
            
            # Vertices
            for v in geom.vertices:
                bm.verts.new(v)

            bm.verts.ensure_lookup_table()
            bm.verts.index_update()

            # Add UV Layers
            for layer in geom.uv_layers:
                uv_layers.append(bm.loops.layers.uv.new())
            
            # Faces (TODO: Materials)
            for f in geom.triangles:
                try:
                    face = bm.faces.new(
                        [
                            bm.verts[f.a],
                            bm.verts[f.b],
                            bm.verts[f.c]
                        ])

                    # Setting faces
                    for i, layer in enumerate(geom.uv_layers):
                        
                        for loop in face.loops:
                            bl_layer = uv_layers[i]

                            uv_coords = layer[loop.vert.index]

                            loop[bl_layer].uv = (
                                uv_coords.u,
                                1 - uv_coords.v # Y coords are flipped in Blender
                            )
                    
                    face.smooth = True
                except BaseException as e:
                    print(e)

            bm.to_mesh(mesh)
            bm.free()

            # Set loop normals
            if geom.has_normals:
                normals = []
                for loop in mesh.loops:
                    normals.append(geom.normals[loop.vertex_index])

                mesh.normals_split_custom_set(normals)
                mesh.use_auto_smooth = True

            mesh.update()
            self.meshes[atomic.frame] = mesh

    #######################################################
    def link_object(obj):
        # Blender 2.79 used scene instead of collections
        scene = bpy.context.scene
        
        if (2, 80, 0) > bpy.app.version:
            scene.objects.link(obj)
        else:
            scene.collection.objects.link(obj)
            
    #######################################################
    def set_empty_draw_properties(empty):
        if (2, 80, 0) > bpy.app.version:
            empty.empty_draw_type = 'CUBE'
            empty.empty_draw_size = 0.05
        else:
            empty.empty_display_type = 'CUBE'
            empty.empty_display_size = 0.05
        pass

    ##################################################################
    def import_materials(geometry):

        self = dff_importer
        
        from bpy_extras.image_utils import load_image
        
        # Blender 2.79 loading
        if (2,80, 0) > bpy.app.version:
            pass

        else:
            from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

            for index, material in enumerate(geometry.materials):

                mat = bpy.data.materials.new(name="Material")
                mat.use_nodes = True
                
                principled = PrincipledBSDFWrapper(mat, is_readonly=False)
                
                principled.base_color = (
                    material.colour.r,
                    material.colour.g,
                    material.colour.b
                )

                # Texture
                print(material.is_textured)
                if material.is_textured == 1:
                    texture = material.textures[0]
                    path = os.path.dirname(self.file_name) + '/' + texture.name + '.png'

                    image = load_image(path)
                    if image is not None:
                        principled.base_color_texture.image = image
                    else:
                        print("Image not found %s" % (path))
                
                props = None

                # Give precedence to the material surface properties
                if material.surface_properties is not None:
                    props = material.surface_properties
                    
                elif geometry.surface_properties is not None:
                    props = geometry.surface_properties

                # TODO: Ambient property in an added panel
                if props is not None:
                    principled.specular = props.specular
                    principled.roughness = props.diffuse                    
                
    
    #######################################################
    def import_frames():
        self = dff_importer

        for index, frame in enumerate(self.dff.frame_list):
            
            if frame.name is None:
                continue

            # Check if the mesh for the frame has been loaded
            mesh = None
            if index in self.meshes:
                mesh = self.meshes[index]

            # Create and link the object to the scene
            obj = bpy.data.objects.new(frame.name, mesh)
            self.link_object(obj)

            # Load matrix
            matrix = mathutils.Matrix(
                (
                    frame.rotation_matrix.right,
                    frame.rotation_matrix.up,
                    frame.rotation_matrix.at
                )
            )
            
            matrix.transpose()

            obj.rotation_mode       = 'QUATERNION'
            obj.rotation_quaternion = matrix.to_quaternion()
            obj.location            = frame.position

            # Set empty display properties to something decent
            if mesh is None:
                self.set_empty_draw_properties(obj)
            
            # set parent
            # Note: I have not considered if frames could have parents
            # that have not yet been defined. If I come across such
            # a model, the code will be modified to support that
            
            if  frame.parent != -1:
                obj.parent = self.objects[frame.parent]

            self.objects.append(obj)
    
    #######################################################
    def import_dff(file_name):
        self = dff_importer
        self._init()

        # Load the DFF
        self.dff = dff()
        self.dff.load_file(file_name)
        self.file_name = file_name

        self.import_atomics()
        self.import_frames()

#######################################################
def import_dff(file_name):

    # Shadow function
    dff_importer.import_dff(file_name)
