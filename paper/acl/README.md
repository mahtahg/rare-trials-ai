# RareMCP: ACL Rolling Review version

Target: ACL 2027 via ARR (submission deadline 4 January 2027). The paper is a long paper: at most 8 pages of content, with unlimited Limitations, Ethics, references and appendix. It must be anonymised.

## Build
    python paper/acl/make_acl.py          # figures, tables and the open-model paragraph from eval/results
    cd paper/acl && latexmk -pdf raremcp_acl.tex

`make_acl.py` reads the saved Claude comparisons. It merges, scores (gold v1.1, all questions) and adds the open-weight runs once every run is present. Until then, those cells read "pending" in red.

## Open-weight runs (free: public repository, CPU runners, llama.cpp)
    gh workflow run eval-open.yml -f model=gemma4-26b-a4b -f run_id=open-gemma4 -f questions=eval/questions.jsonl -f shards='[0,1,2,3,4,5,6,7]' -f n_shards=8
    gh workflow run eval-open.yml -f model=gemma4-26b-a4b -f run_id=open-gemma4-hard -f questions=eval/questions_hard.jsonl -f shards='[0,1]' -f n_shards=2
    gh workflow run eval-open.yml -f model=gpt-oss-20b -f run_id=open-gptoss -f questions=eval/questions.jsonl -f shards='[0,1,2,3,4,5,6,7]' -f n_shards=8
    gh workflow run eval-open.yml -f model=gpt-oss-20b -f run_id=open-gptoss-hard -f questions=eval/questions_hard.jsonl -f shards='[0,1]' -f n_shards=2

Re-run the same command to resume a shard that hit its time budget. Completed runs are skipped.

## Before submission
See the red items in the PDF and the TO DO items in `responsible_nlp_checklist.md`. Do not also submit the npj Digital Medicine version: ARR forbids dual submission.
