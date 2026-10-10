"""Compare two Gerber layers without modifying either input."""
import argparse,hashlib,json
from pathlib import Path
from gerber_geometry import render
from geometry_coverage import directed_coverage

def main():
    p=argparse.ArgumentParser();p.add_argument('left',type=Path);p.add_argument('right',type=Path)
    p.add_argument('--epsilon-mil',type=float,default=.001);p.add_argument('--tolerance-mil',type=float,default=.01)
    args=p.parse_args()
    if not (args.epsilon_mil>0 and args.tolerance_mil>0):p.error('Numerical epsilon and comparison tolerance must be positive')
    left,ls=render(args.left,args.epsilon_mil);right,rs=render(args.right,args.epsilon_mil)
    missing,extra,tiles,radius=directed_coverage(left,right,args.tolerance_mil,1000)
    result={'left_sha256':hashlib.sha256(args.left.read_bytes()).hexdigest(),'right_sha256':hashlib.sha256(args.right.read_bytes()).hexdigest(),
      'epsilon_mil':args.epsilon_mil,'comparison_radius_mil':radius,'missing_area_mil2':missing.area,'extra_area_mil2':extra.area,
      'left_parser':ls,'right_parser':rs,'interpretation':'geometric evidence, not board or manufacturing signoff'}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
