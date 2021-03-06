#!/usr/bin/env python

import sys,os,errno,argparse,subprocess
from Bio import SeqIO

helptext = """

usage: python distribute_targets.py baitfile\n


Given a file containing all of the "baits" for a target enrichment, create separate
FASTA files with all copies of that bait. Multiple copies of the same bait can be 
specified using a "-" delimiter. For example, the following will be sorted in to the same
file:

Anomodon-rbcl
Physcomitrella-rbcl

The results can come from either BLASTx or BWA.

Given multiple baits, the script will choose the most appropriate 'reference' sequence
using the highest cumulative BLAST scores or Mapping Quality across all hits.

Output directories can also be created, one for each target category
	(the default is to put them all in the current one)
The field delimiter may also be changed.
"""


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def tailored_target_blast(blastxfilename):
	"""Determine, for each protein, the 'best' target protein, by tallying up the blastx hit scores."""
	blastxfile = open(blastxfilename)
	
	hitcounts = {}
	for result in blastxfile:
		result = result.split()
		hitname = result[1].split("-")
		bitscore = float(result[-1])
		protname = hitname[1]
		taxon = hitname[0]
		if protname in hitcounts:
			if taxon in hitcounts[protname]:
				hitcounts[protname][taxon] += bitscore
			else:
				hitcounts[protname][taxon] = bitscore
		else:
			hitcounts[protname] = {taxon:1}
	#For each protein, find the taxon with the highest total hit bitscore.
	besthits = {}
	besthit_counts = {}
	for prot in hitcounts:
		top_taxon = sorted(hitcounts[prot].iterkeys(), key = lambda k: hitcounts[prot][k], reverse=True)[0]
		besthits[prot] = top_taxon
		if top_taxon in besthit_counts:
			besthit_counts[top_taxon] += 1
		else:
			besthit_counts[top_taxon] = 1
	tallyfile = open("bait_tallies.txt",'w')
	for x in besthit_counts:
		tallyfile.write("{}\t{}\n".format(x, besthit_counts[x]))
	tallyfile.close()
	return besthits		

def tailored_target_bwa(bamfilename):
	"""Determine, for each protein, the 'best' target protein, by tallying up the blastx hit scores."""
	samtools_cmd = "samtools view -F 4 {}".format(bamfilename)
	child = subprocess.Popen(samtools_cmd,shell=True,stdout=subprocess.PIPE)
	bwa_results = child.stdout.readlines()
		
	hitcounts = {}
	for result in bwa_results:
		result = result.split()
		hitname = result[2].split("-")
		mapscore = float(result[4])
		protname = hitname[1]
		taxon = hitname[0]
		if protname in hitcounts:
			if taxon in hitcounts[protname]:
				hitcounts[protname][taxon] += mapscore
			else:
				hitcounts[protname][taxon] = mapscore
		else:
			hitcounts[protname] = {taxon:1}
	#For each protein, find the taxon with the highest total hit mapscore.
	besthits = {}
	besthit_counts = {}
	for prot in hitcounts:
		top_taxon = sorted(hitcounts[prot].iterkeys(), key = lambda k: hitcounts[prot][k], reverse=True)[0]
		besthits[prot] = top_taxon
		if top_taxon in besthit_counts:
			besthit_counts[top_taxon] += 1
		else:
			besthit_counts[top_taxon] = 1
	tallyfile = open("bait_tallies.txt",'w')
	for x in besthit_counts:
		tallyfile.write("{}\t{}\n".format(x, besthit_counts[x]))
	tallyfile.close()
	return besthits	
        
def distribute_targets(baitfile,dirs,delim,besthits,translate=False):
	targets = SeqIO.parse(baitfile,'fasta')
	no_matches = []
	for prot in targets:
		#Get the 'basename' of the protein
		prot_cat = prot.id.split(delim)[-1]
		if translate:
			prot.seq = prot.seq.translate()
		
		if dirs:
			mkdir_p(prot_cat)
		if prot_cat in besthits:        
			besthit_taxon = besthits[prot_cat]
			if prot.id.split("-")[0] == besthit_taxon:
				#print "Protein {} is a best match to {}".format(prot_cat,besthit_taxon)
				outfile = open(os.path.join(prot_cat,"{}_baits.fasta".format(prot_cat)),'w')
				SeqIO.write(prot,outfile,'fasta')
				outfile.close()
		else:
			no_matches.append(prot_cat)
	print "{} proteins had no good matches.".format(len(set(no_matches)))
	#print besthits.values()			

		

def help():
	print helptext
	return
		
def main():
	parser = argparse.ArgumentParser(description=helptext,formatter_class=argparse.RawTextHelpFormatter)
	parser.add_argument("--no_dirs",help="Do not generate separate directories for each protein-- output all to the current directory.", action="store_true",default=False)
	parser.add_argument("-d","--delimiter",help="Field separating FASTA ids for multiple sequences per target. Default is '-' . For no delimeter, write None", default="-")
	parser.add_argument("baitfile",help="FASTA file containing bait sequences")
	parser.add_argument("--blastx",help="tabular blastx results file, used to select the best target for each gene",default=None)
	parser.add_argument("--bam",help="BAM file from BWA search, alternative to the BLASTx method",default=None)
	args = parser.parse_args()
	
	if args.no_dirs:
		if args.blastx:
			besthits = tailored_target_blast(args.blastx)
			distribute_targets(args.baitfile,dirs=True,delim=args.delimiter,besthits=besthits)
		elif args.bam:
			besthits = tailored_target_bwa(args.bam)
			distribute_targets(args.baitfile,dirs=True,delim=args.delimiter,besthits=besthits,translate=True)
	else:
		if args.blastx:
			besthits = tailored_target_blast(args.blastx)
			distribute_targets(args.baitfile,dirs=True,delim=args.delimiter,besthits=besthits)
		elif args.bam:
			besthits = tailored_target_bwa(args.bam)
			distribute_targets(args.baitfile,dirs=True,delim=args.delimiter,besthits=besthits,translate=True)
	


if __name__=="__main__":main()