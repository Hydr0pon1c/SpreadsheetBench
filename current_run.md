1. 先跑 skill0 on evolve 200，生成 Creation 用轨迹

cd inference
python3 inference_multiple.py \
--setting row_react_exec \
--model qwen3.5-35b-a3b \
--base_url https://dashscope.aliyuncs.com/compatible-mode/v1 \
--dataset spreadsheetbench_verified_400 \
--split_file ../data/splits/verified_evolve_200.json \
--skill_path ../skills/spreadsheet-parametric-qwen3.5-35b-a3b/SKILL.md \
--run_name qwen3.5-35b-a3b_parametric_evolve \
--code_exec_url http://localhost:8081/execute \
--skip_existing

跑完后重算并评估：

cd ../evaluation
python3 open_spreadsheet.py \
--dir_path ../data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b_parametric_evolve \
--backend libreoffice

python3 evaluation.py \
--setting multi_row_react_exec \
--model qwen3.5-35b-a3b \
--dataset spreadsheetbench_verified_400 \
--split_file ../data/splits/verified_evolve_200.json \
--run_name qwen3.5-35b-a3b_parametric_evolve

2. 再跑 skill0 on test 200，得到 Parametric baseline

cd ../inference
python3 inference_multiple.py \
--setting row_react_exec \
--model qwen3.5-35b-a3b \
--api_key API_KEY \
--base_url https://dashscope.aliyuncs.com/compatible-mode/v1 \
--dataset spreadsheetbench_verified_400 \
--split_file ../data/splits/verified_test_200.json \
--skill_path ../skills/spreadsheet-parametric-qwen3.5-35b-a3b/SKILL.md \
--run_name qwen3.5-35b-a3b_parametric_test \
--code_exec_url http://localhost:8081/execute \
--skip_existing

对应评估：

cd ../evaluation
python3 open_spreadsheet.py \
--dir_path ../data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b_parametric_test \
--backend libreoffice

python3 evaluation.py \
--setting multi_row_react_exec \
--model qwen3.5-35b-a3b \
--dataset spreadsheetbench_verified_400 \
--split_file ../data/splits/verified_test_200.json \
--run_name qwen3.5-35b-a3b_parametric_test
3. 有 evolve 结果后，清洗轨迹

cd ..
python3 trace2skill/prepare_trajectories.py \
--run_id qwen35_parametric_creation_v1 \
--split_file data/splits/verified_evolve_200.json \
--conv_jsonl inference/outputs/conv_multi_row_react_exec_qwen3.5-35b-a3b_parametric_evolve.jsonl \
--eval_json outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b_parametric_evolve.json \
--output_dir data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b_parametric_evolve

• 接下来就是三步：全量生成 patch，合并 patch，应用成 skill*。

先跑 131 条失败轨迹的 Error Analyst patch：

DASHSCOPE_API_KEY='sk-658ff2c442984a10bcdc0a9abe3df395' python3 trace2skill/propose_patches.py \
--run_id qwen35_parametric_creation_v1 \
--skill_path skills/spreadsheet-parametric-qwen3.5-35b-a3b/SKILL.md \
--model qwen3.5-122b-a10b

产出会在：

trace2skill_runs/qwen35_parametric_creation_v1/patches/error/

然后合并这些 patch：

DASHSCOPE_API_KEY='你的 key' python3 trace2skill/merge_patches.py \
--run_id qwen35_parametric_creation_v1 \
--model qwen3.5-122b-a10b \
--batch_size 32 \
--seed 0

产出：

trace2skill_runs/qwen35_parametric_creation_v1/merges/final_patch.json

最后应用到 skill0，得到演化后的 skill：

python3 trace2skill/apply_skill_patch.py \
--run_id qwen35_parametric_creation_v1 \
--skill0 skills/spreadsheet-parametric-qwen3.5-35b-a3b/SKILL.md

最终文件：

trace2skill_runs/qwen35_parametric_creation_v1/skill_star/SKILL.md

跑完第一步后建议先检查 rejected 数量：

find trace2skill_runs/qwen35_parametric_creation_v1/patches/error/rejected -type f | wc -l

如果 rejected 很少或为 0，就继续 merge。

用最终合成的 skill 跑 test split，分三步：inference、recalc、eval。

1. 跑 inference

cd inference

python3 inference_multiple.py \
--setting row_react_exec \
--model qwen3.5-35b-a3b \
--api_key sk-658ff2c442984a10bcdc0a9abe3df395 \
--base_url https://dashscope.aliyuncs.com/compatible-mode/v1 \
--dataset spreadsheetbench_verified_400 \
--split_file ../data/splits/verified_test_200.json \
--skill_path ../trace2skill_runs/qwen35_parametric_creation_v1/skill_star/SKILL.md \
--run_name qwen3.5-35b-a3b_skill_star_test \
--code_exec_url http://localhost:8081/execute \
--skip_existing

输出会写到：

inference/outputs/conv_multi_row_react_exec_qwen3.5-35b-a3b_skill_star_test.jsonl
data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b_skill_star_test/

2. 重新打开/重算 xlsx

cd ../evaluation

python3 open_spreadsheet.py \
--dir_path ../data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b_skill_star_test \
--backend libreoffice

3. 跑 evaluation

python3 evaluation.py \
--setting multi_row_react_exec \
--model qwen3.5-35b-a3b \
--dataset spreadsheetbench_verified_400 \
--split_file ../data/splits/verified_test_200.json \
--run_name qwen3.5-35b-a3b_skill_star_test

结果文件会是：

outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b_skill_star_test.json

最后可以汇总三组结果：

cd ..

python3 trace2skill/summarize_results.py \
--run_id qwen35_parametric_creation_v1 \
--split_file data/splits/verified_test_200.json \
--eval_no_skill outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b.json \
--eval_skill0 outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b_parametric_test.json \
--eval_skill_star outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b_skill_star_test.json

汇总报告会写到：

trace2skill_runs/qwen35_parametric_creation_v1/report.md