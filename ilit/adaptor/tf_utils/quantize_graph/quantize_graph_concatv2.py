#  -*- coding: utf-8 -*-
from tensorflow.python.framework import dtypes
from tensorflow.core.framework import node_def_pb2
from .quantize_graph_base import QuantizeNodeBase
from .quantize_graph_common import QuantizeGraphHelper as helper

import re


class FuseNodeStartWithConcatV2(QuantizeNodeBase):
    def __init__(self, input_graph, output_node_names, perchannel,
                start_node_name, _):
        super(FuseNodeStartWithConcatV2,
              self).__init__(input_graph, output_node_names, perchannel,
                             start_node_name)

    def _apply_concatv2_transform(self, original_node):
        namespace_prefix = original_node.name + "_eightbit"
        quantized_concat_name = namespace_prefix + "_quantized_concatv2"
        reshape_dims_name, reduction_dims_name = self._add_common_quantization_nodes(
            namespace_prefix, helper.node_name_from_input(original_node.input[-1]))
        num_input = len(original_node.input)
        shape_input_name = original_node.input[num_input - 1]
        original_inputs = original_node.input[0:num_input - 1]
        input_names = []
        min_names = []
        max_names = []
        for original_input_name in original_inputs:
            quantize_input_name, min_input_name, max_input_name = (
                self._eightbitize_input_to_node(namespace_prefix,
                                                original_input_name,
                                                reshape_dims_name,
                                                reduction_dims_name,
                                                dtype=dtypes.quint8))
            input_names.append(quantize_input_name)
            min_names.append(min_input_name)
            max_names.append(max_input_name)
        all_input_names = input_names
        all_input_names.append(shape_input_name)
        all_input_names.extend(min_names)
        all_input_names.extend(max_names)
        quantized_concat_node = helper.create_node("QuantizedConcatV2",
                                                   quantized_concat_name,
                                                   all_input_names)
        helper.set_attr_int(quantized_concat_node, "N", len(original_inputs))
        helper.set_attr_dtype(quantized_concat_node, "T", dtypes.quint8)
        self.add_output_graph_node(quantized_concat_node)
        self._intel_cpu_add_dequantize_result_node(quantized_concat_name,
                                                    original_node.name)


    def _quantizable_concat(self, node):
        for input_node_name in node.input[:node.attr['N'].i]:
            if self.node_name_mapping[helper.node_name_from_input(
                    input_node_name)].node.op != "Dequantize":
                return False
        return True

    def _apply_concatv2_quantization(self):
        for _, v in self.node_name_mapping.items():
            if v.node.op in ("ConcatV2") and self._quantizable_concat(
                    v.node) and not re.search(
                        r'map(_\d+)?/while', v.node.name) and dtypes.as_dtype(
                            v.node.attr["T"].type) == dtypes.float32:
                self._apply_concatv2_transform(v.node)
            else:
                new_node = node_def_pb2.NodeDef()
                new_node.CopyFrom(v.node)
                self.add_output_graph_node(new_node)

    def get_longest_fuse(self):
        return 1

    def apply_the_transform(self):
        self._apply_concatv2_quantization()
        self._reset_output_node_maps()

        self.output_graph = self.remove_redundant_quantization(
            self.output_graph)
        # self.remove_dead_nodes(self.output_node_names)
        return self.output_graph
