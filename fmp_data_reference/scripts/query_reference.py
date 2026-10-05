"""Search the large dictionary without loading it into a model context."""
import argparse,csv,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--api',required=True)
    parser.add_argument('--field',default='')
    parser.add_argument('--limit',type=int,default=15)
    args=parser.parse_args()
    if not 1<=args.limit<=100:raise SystemExit('Choose a result limit between 1 and 100.')
    count=0;csv.field_size_limit(8*1024*1024)
    with (ROOT/'data_dictionary.csv').open(encoding='utf-8',newline='') as f:
        for row in csv.DictReader(f):
            if row['api_id']!=args.api.upper() or args.field.lower() not in row['field_path'].lower():continue
            selected={k:row[k] for k in ['api_id','field_path','definition','definition_status','observed_json_types','example_values_json','units','null_count','missing_in_observed_parent_objects','official_documentation','schema_basis']}
            selected['sample_files']=json.loads(row['sample_files_json'])[:3]
            print(json.dumps(selected,ensure_ascii=False));count+=1
            if count>=args.limit:break
    print('Matched results shown:',count)

if __name__=='__main__':main()
