import math
import numpy as np

# Custom
import pypattern as pyp
from . import skirt_paneled as skirts

class Insert(pyp.Panel):
    def __init__(self, id, width=30, depth=30) -> None:
        super().__init__(f'Insert_{id}')

        self.edges = pyp.esf.from_verts([0, 0], [width/2, depth], [width, 0], loop=True)

        self.interfaces = [
            pyp.Interface(self, self.edges[:2])
        ]
        self.top_center_pivot()
        self.center_x()

class GodetSkirt(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}')

        gdesign = design['godet-skirt']
        ins_w = gdesign['insert_w']['v']
        ins_depth = gdesign['insert_depth']['v']

        base_skirt = getattr(skirts, gdesign['base']['v'])
        self.base = base_skirt(body, design)

        # TODO resolve collisions on inserts placement
        bintr = self.base.interfaces['bottom']
        for edge, panel in zip(bintr.edges, bintr.panel):
            self.inserts(
                edge, panel, ins_w, ins_depth , 
                num_inserts=gdesign['num_inserts']['v'] / len(bintr), 
                cuts_dist=gdesign['cuts_distance']['v'])

        self.interfaces = {
            'top': self.base.interfaces['top']
        }


    def inserts(
            self, bottom_edge, panel, ins_w, ins_depth,
            num_inserts=3, cuts_dist=0):
        """Create insert panels, add cuts to the skirt panel, 
            and connect created insert panels with them
        """

        num_inserts = int(num_inserts)
        bottom_len = bottom_edge.length()

        pbbox = panel.bbox3D()
        z_transl = panel.translation[-1] + np.sign(panel.translation[-1]) * 5
        y_base = pbbox[0][1]   # min Y
        x_shift = (pbbox[0][0] + pbbox[1][0]) / 2

        cut_width = (bottom_len - cuts_dist * num_inserts) / num_inserts 
        if cut_width < 1:
            print(f'{self.__class__.__name__}::Warning:: Cannot place {num_inserts} cuts '
                  'with requested distance between cuts {cuts_dist}. Using the maximum possible distance')
            cut_width = 1  # 1 cm 
            cuts_dist = (bottom_len - cut_width * num_inserts) / num_inserts

        # Insert panels
        insert = Insert(0, width=ins_w, depth=ins_depth).translate_by([
            x_shift - num_inserts * ins_w / 2 + ins_w / 2, y_base + ins_depth, z_transl])
        self.subs += pyp.ops.distribute_horisontally(insert, num_inserts, -ins_w, panel.name)

        # make appropriate cuts and stitches
        cut_depth = math.sqrt((ins_w / 2)**2 + ins_depth**2 - (cut_width / 2)**2)
        cut_shape = pyp.esf.from_verts([0,0], [cut_width / 2, cut_depth], [cut_width, 0])  

        right = z_transl < 0    # FIXME: heuristic corresponding to skirts in our collection

        # DRAFT right = panel.is_right_inside_edge(bottom_edge) =( Does not work reliably!

        for i in range(num_inserts):
            offset = cut_width / 2 + (cuts_dist / 2 if i == 0 else cuts_dist)   #  start_offest + i * stride

            # DEBUG
            print(offset, ' out of ', bottom_edge.length())

            new_bottom, cutted, _ = pyp.ops.cut_into_edge(
                cut_shape, bottom_edge, offset=offset, right=right)
            panel.edges.substitute(bottom_edge, new_bottom)
            bottom_edge = new_bottom[-1]  # New edge that needs to be cutted -- on the next step

            cut_interface = pyp.Interface(panel, cutted)
            if right: 
                cut_interface.reverse()

            self.stitching_rules.append(
                (self.subs[-1-i if right else -(num_inserts-i)].interfaces[0], 
                cut_interface))
       
