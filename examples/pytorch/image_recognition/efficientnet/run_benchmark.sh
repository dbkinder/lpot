#!/bin/bash
set -x

function main {

  init_params "$@"
  run_benchmark

}

# init params
function init_params {
  iters=100
  if [ "${topology}" = "efficientnet_b0" ];then
      tuned_checkpoint=lpot_workspace/pytorch/efficient_b0/checkpoint
  elif [ "${topology}" = "mobilenetv3_rw" ]; then
      tuned_checkpoint=lpot_workspace/pytorch/mobilenetv3_rw/checkpoint
  fi
  batch_size=30
  for var in "$@"
  do
    case $var in
      --topology=*)
          topology=$(echo $var |cut -f2 -d=)
      ;;
      --dataset_location=*)
          dataset_location=$(echo $var |cut -f2 -d=)
      ;;
      --input_model=*)
          input_model=$(echo $var |cut -f2 -d=)
      ;;
      --mode=*)
          mode=$(echo $var |cut -f2 -d=)
      ;;
      --batch_size=*)
          batch_size=$(echo $var |cut -f2 -d=)
      ;;
      --iters=*)
          iters=$(echo ${var} |cut -f2 -d=)
      ;;
      --int8=*)
          int8=$(echo ${var} |cut -f2 -d=)
      ;;
      *)
          echo "Error: No such parameter: ${var}"
          exit 1
      ;;
    esac
  done

}


# run_benchmark
function run_benchmark {
    python setup.py install
    if [[ ${mode} == "accuracy" ]]; then
        mode_cmd=" --benchmark"
    elif [[ ${mode} == "benchmark" ]]; then
        mode_cmd=" -i ${iters} --benchmark "
    else
        echo "Error: No such mode: ${mode}"
        exit 1
    fi

    if [[ ${int8} == "true" ]]; then
        extra_cmd="--int8 ${dataset_location}"
    else
        extra_cmd="--pretrained ${dataset_location}"
    fi

    python -u validate.py \
        --tuned_checkpoint ${tuned_checkpoint} \
        --model $topology \
        -b ${batch_size} \
        --no-cuda \
        -j 1 \
        ${mode_cmd} \
        ${extra_cmd}
}

main "$@"
