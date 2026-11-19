ROOT_FOLDER=.
LANGUAGE=kr
MODEL=qwenvlchat

python src/eval.py \
    --inference_result $ROOT_FOLDER/inference_results/${MODEL}_${LANGUAGE}.json \
    --save_path $ROOT_FOLDER/results/${MODEL}_${LANGUAGE}.json \
    --language $LANGUAGE
