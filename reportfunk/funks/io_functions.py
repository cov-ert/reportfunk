#!/usr/bin/env python3

import os
import argparse
import csv
import datetime 
import sys
from Bio import SeqIO
from datetime import datetime 
import tempfile
import pkg_resources
import yaml

END_FORMATTING = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[93m'
CYAN = '\u001b[36m'
DIM = '\033[2m'

def make_config_file(config):
    config_to_write = {}
    for k in config:
        if k != "generate_config":
            config_to_write[k] = config[k]
    config_out = os.path.join(config["outdir"],"civet_config.yaml")
    with open(config_out,"w") as fw:
        yaml.dump(config_to_write, fw)
        print(green(f"Config file written to {config_out}."))
        sys.exit()

def type_input_file(input_arg,cwd,config):

    query,configfile="",""
    if input_arg:
        if "," in input_arg:
            id_list = input_arg.split(",")
            query = make_csv_from_ids(id_list, config)
            config["path_to_query"] = config["outdir"]
        else:
            input_file = os.path.join(cwd,input_arg)
            path_to_file = os.path.abspath(os.path.dirname(input_file))
            config["path_to_query"] = path_to_file

            ending = input_file.split(".")[-1]

            if ending in ["yaml","yml"]:
                print(green(f"Input config file:") + f" {input_file}")
                configfile  = input_file

            elif ending == "csv":
                print(green(f"Input file:") + f" {input_file}")
                query = input_file

    return query,configfile
    
def make_csv_from_ids(id_list, config):
    query = os.path.join(config["outdir"], "query.csv")
    with open(query,"w") as fw:
        in_col = config["input_column"]
        fw.write(f"{in_col}\n")
        for i in id_list:
            fw.write(i+'\n')
    return query

def parse_yaml_file(configfile,config):
    with open(configfile,"r") as f:
        input_config = yaml.load(f, Loader=yaml.FullLoader)
        for key in input_config:
            snakecase_key = key.replace("-","_")
            if not snakecase_key in config:
                config[snakecase_key] = input_config[key]

    return config

def get_snakefile(thisdir):
    snakefile = os.path.join(thisdir, 'scripts','Snakefile')
    if not os.path.exists(snakefile):
        sys.stderr.write(cyan(f'Error: cannot find Snakefile at {snakefile}\n Check installation'))
        sys.exit(-1)
    return snakefile

def get_query_fasta(fasta_arg,cwd,config):

    if fasta_arg:
        fasta = os.path.join(cwd, fasta_arg)

    elif "fasta" in config:
        fasta = os.path.join(config["path_to_query"], config["fasta"]) #do we want capability for having different paths to fasta? Or we could ask them to provide full path in config.

    else:
        fasta = ""

    if fasta:
        if not os.path.exists(fasta):
            sys.stderr.write(cyan(f'Error: cannot find fasta query at {fasta}\n'))
            sys.exit(-1)
        else:
            print(green(f"Input fasta file:") + f" {fasta}")
    
    config["fasta"] = fasta 

def get_outdir(outdir_arg,cwd,config):
    outdir = ''
    
    if outdir_arg:
        rel_outdir = outdir_arg #for report weaving
        outdir = os.path.join(cwd, outdir_arg)

    elif "outdir" in config:
        rel_outdir = config["outdir"]
        outdir = os.path.join(cwd, rel_outdir)

    else:
        timestamp = str(datetime.now().isoformat(timespec='milliseconds')).replace(":","").replace(".","").replace("T","-")
        outdir = os.path.join(cwd, timestamp)
        
        rel_outdir = os.path.join(".",timestamp)
        
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    print(green(f"Output dir:") + f" {outdir}")
    config["outdir"] = outdir 
    config["rel_outdir"] = rel_outdir 
        
def get_temp_dir(tempdir_arg,no_temp_arg, cwd,config):
    tempdir = ''
    outdir = config["outdir"]
    if no_temp_arg:
        print(green(f"--no-temp:") + f" All intermediate files will be written to {outdir}")
        tempdir = outdir
    elif "no-temp" in config:
        print(green(f"--no-temp:") + f" All intermediate files will be written to {outdir}")
        tempdir = outdir
    elif tempdir_arg:
        to_be_dir = os.path.join(cwd, tempdir_arg)
        if not os.path.exists(to_be_dir):
            os.mkdir(to_be_dir)
        temporary_directory = tempfile.TemporaryDirectory(suffix=None, prefix=None, dir=to_be_dir)
        tempdir = temporary_directory.name

    elif "tempdir" in config:
        to_be_dir = os.path.join(cwd, config["tempdir"])
        if not os.path.exists(to_be_dir):
            os.mkdir(to_be_dir)
        temporary_directory = tempfile.TemporaryDirectory(suffix=None, prefix=None, dir=to_be_dir)
        tempdir = temporary_directory.name

    else:
        temporary_directory = tempfile.TemporaryDirectory(suffix=None, prefix=None, dir=None)
        tempdir = temporary_directory.name
    
    config["tempdir"] = tempdir 
    return tempdir

def check_query_file(query, cwd, config):
    queryfile = ""
    
    if query:
        queryfile = query

    elif "query" in config:
        queryfile = os.path.join(config["path_to_query"],config["query"])

    elif "ids" in config:
        queryfile = make_csv_from_ids(config["ids"], config)

    else:
        sys.stderr.write(cyan(f"Error: no query input provided"))
        sys.exit(-1)

    print("queryfile is",queryfile)
    if os.path.exists(queryfile):
        config["query"] = queryfile
    else:
        sys.stderr.write(cyan(f"Error: cannot find query file at {queryfile}\nCheck if the file exists, or if you're inputting a set of ids (e.g. EPI12345,EPI23456), please use in conjunction with the `--id-string` flag or provide `ids` in the config file \n."))
        sys.exit(-1)

def local_lineages_to_config(central, neighbouring, region, config):

    if config["local_lineages"] == True:
        lineage_tables = []
        for r,d,f in os.walk(os.path.join(config["outdir"], 'figures')):
            for fn in f:
                if fn.endswith("_lineageTable.md"):
                    lineage_tables.append(os.path.join(config["outdir"], 'figures', fn))

        config["lineage_tables"] = lineage_tables
        config["lineage_maps"] = [central, neighboring, region]
    else:
        config["lineage_tables"] = []
        config["lineage_maps"] = []


def get_tree_name_stem(tree_dir,config):
    tree_name_stems = []
    for r,d,f in os.walk(tree_dir):
        for fn in f:
            if fn.endswith(".tree"):
                basename = ".".join(fn.split(".")[:-1])
                stem = "_".join(basename.split("_")[:-1])
                tree_name_stems.append(stem)
    tree_name_stems = list(set(tree_name_stems))
    
    if len(tree_name_stems) > 1:
        sys.stderr.write("Error: Multiple tree names found")
        sys.exit(-1)
    elif len(tree_name_stems) == 0:
        sys.stderr.write("Error: No trees found in tree directory.")
        sys.exit(-1)
    else:
        tree_name_stem = tree_name_stems[0]

    config["tree_name_stem"] = tree_name_stem



def check_args_and_config_list(argument, config_key, default, column_names, config):

    full_metadata_headers = get_full_headers()

    list_of_fields = []
    arg_list = []
    if argument:
        arg_list = argument.split(",")
        for field in arg_list:
            if field in column_names or field in full_metadata_headers:
                list_of_fields.append(field)
            else:
                sys.stderr.write(cyan(f"Error: {field} field not found in query metadata file or background metadata file\n"))
                sys.exit(-1)

    elif config_key in config:
        if type(config[config_key]) != list:
            arg_list = config[config_key].split(",")
        else:
            arg_list = config[config_key]

        for field in arg_list:
            if field in column_names  or field in full_metadata_headers:
                list_of_fields.append(field)
            else:
                sys.stderr.write(cyan(f"Error: {field} field not found in  query metadata file or background metadata file\n"))
                sys.exit(-1)

    else:
        arg_list.append(default)        
        
    field_str = ",".join(arg_list)
    return field_str

def node_summary(node_summary,config):
    with open(config["cog_global_metadata"], newline="") as f:
        reader = csv.DictReader(f)
        column_names = reader.fieldnames

        if not node_summary:
            summary = "country"
        else:
            if node_summary in column_names:
                summary = node_summary
            else:
                sys.stderr.write(cyan(f"Error: {node_summary} field not found in metadata file\n"))
                sys.exit(-1)
        
        print(green(f"Summarise collapsed nodes by:") + f" {summary}")
        config["node_summary"] = summary

def check_label_and_colour_and_date_fields(colour_fields, label_fields, display_arg, date_fields, input_column, config):
    
    acceptable_colours = get_colours()
    queries = []
    
    labels = []

    graphics_list = []
    query_file = config["query"]
    input_column = config["input_column"]
    column_names = []

    with open(query_file, newline="") as f:
        reader = csv.DictReader(f)
        column_names = reader.fieldnames

        if input_column not in column_names: # Checking input column present in query file
            sys.stderr.write(cyan(f"Error: Query file missing header field {input_column}\n"))
            sys.exit(-1)

        print(green("Input querys to process:"))
        queries = []
        for row in reader:
            queries.append(row[input_column])
            print(f" - {row[input_column]}")
        print(green(f"Number of queries:") + f" {len(queries)}")

    colour_field_str = check_args_and_config_list(colour_fields, "fields", "adm1", column_names, config)
    print(green(f"Colouring by:") + f" {colour_field_str}")
    config["tree_fields"] = colour_field_str
        
    labels_str = check_args_and_config_list(label_fields, "label_fields", "NONE", column_names, config)

    print(green(f"Labelling by:") + f" {labels_str}")
    config["label_fields"] = labels_str

    date_field_str = check_args_and_config_list(date_fields,"date_fields","NONE", column_names,config)
    config["date_fields"] = date_field_str

    if display_arg:
        sections = display_arg.split(",")
        for item in sections:
            splits = item.split("=")
            graphic_trait = splits[0]
            if graphic_trait in column_names:
                if len(splits) == 1:
                    graphics_list.append(graphic_trait + ":default")
                else:
                    colour_scheme = splits[1]
                    if colour_scheme in acceptable_colours:
                        graphics_list.append(graphic_trait + ":" + colour_scheme)
                    else:
                        sys.stderr.write(cyan(f"Error: {colour_scheme} not a matplotlib compatible colour scheme\n"))
                        sys.stderr.write(cyan(f"Please use one of {acceptable_colours}"))
                        sys.exit(-1)
            else:
                sys.stderr.write(cyan(f"Error: {graphic_trait} field not found in metadata file\n"))
                sys.exit(-1)
    else:
        graphics_list.append("adm1:default")

    config["graphic_dict"] = ",".join(graphics_list)

def map_sequences_config(map_sequences,mapping_trait,map_inputs,input_crs,query,config):
        map_settings = False

        if map_sequences:
            map_settings = True
            
        elif "map_sequences" in config:
            map_settings = config["map_sequences"]
        
        if map_settings:
            if not map_inputs:
                sys.stderr.write(cyan('Error: coordinates or outer postcode not supplied for mapping sequences. Please provide either x and y columns as a comma separated string, or column header containing outer postcode.'))
                sys.exit(-1)
            else:
                
                if len(map_inputs.split(",")) == 2: #If x and y coordinates are provided
                    if not input_crs:
                        sys.stderr.write('Error: input coordinate system not provided for mapping. Please provide --input-crs eg EPSG:3395')
                        sys.exit(-1)
                    else:
                        crs = input_crs
                else: #If an outer postcode column is provided        
                    crs = "EPSG:4326"
                                
                config["map_cols"] = map_inputs
                config["input_crs"] = crs

            with open(query, newline="") as f:
                reader = csv.DictReader(f)
                column_names = reader.fieldnames
                relevant_cols = []
                map_inputs_lst = map_inputs.split(",")
                for i in map_inputs_lst:
                    relevant_cols.append(i)
                relevant_cols.append(mapping_trait)
                
                for map_arg in relevant_cols:

                    if map_arg not in column_names:
                        sys.stderr.write(cyan(f"Error: {map_arg} field not found in metadata file"))
                        sys.exit(-1)

            if mapping_trait:
                config["mapping_trait"] = mapping_trait
            else:
                config["mapping_trait"] = False
                
        else:
            config["map_sequences"] = False
            config["map_cols"] = False
            config["input_crs"] = False
            config["mapping_trait"] = False

def local_lineages_config(local_lineages, query, config):

        if "local_lineages" in config:
            pass
        elif local_lineages:
            config['local_lineages'] = True
        else:
            config["local_lineages"] = False

        if config["local_lineages"]:
            with open(query, newline="") as f:
                reader = csv.DictReader(f)
                header = reader.fieldnames
                if not "adm2" in header:
                    sys.stderr.write(cyan(f"Error: --local-lineages argument called, but input csv file doesn't have an adm2 column. Please provide that to have local lineage analysis.\n"))
                    sys.exit(-1)
        else:
            config['local_lineages'] = False


def check_summary_fields(full_metadata, summary_field, config):

    with open(full_metadata, newline="") as f:
        reader = csv.DictReader(f)
        column_names = reader.fieldnames

        if not summary_field:
                summary = "lineage"
        else:
            if summary_field in column_names:
                summary = summary_field
            else:
                sys.stderr.write(cyan(f"Error: {summary_field} field not found in metadata file\n"))
                sys.exit(-1)
        
        print(green(f"Going to summarise collapsed nodes by: ") + f"{summary}")
        config["node_summary"] = summary


def input_file_qc(minlen,maxambig,config):
    post_qc_query = ""
    qc_fail = ""
    fasta = config["fasta"]
    if fasta != "":
        do_not_run = []
        run = []
        for record in SeqIO.parse(fasta, "fasta"):
            if len(record) <minlen:
                record.description = record.description + f" fail=seq_len:{len(record)}"
                do_not_run.append(record)
                print(cyan(f"    - {record.id}\tsequence too short: Sequence length {len(record)}"))
            else:
                num_N = str(record.seq).upper().count("N")
                prop_N = round((num_N)/len(record.seq), 2)
                if prop_N > maxambig: 
                    record.description = record.description + f" fail=N_content:{prop_N}"
                    do_not_run.append(record)
                    print(cyan(f"    - {record.id}\thas an N content of {prop_N}"))
                else:
                    run.append(record)

        post_qc_query = os.path.join(config["outdir"], 'query.post_qc.fasta')
        with open(post_qc_query,"w") as fw:
            SeqIO.write(run, fw, "fasta")
        qc_fail = os.path.join(config["outdir"],'query.failed_qc.csv')
        with open(qc_fail,"w") as fw:
            fw.write("name,reason_for_failure\n")
            for record in do_not_run:
                desc = record.description.split(" ")
                for i in desc:
                    if i.startswith("fail="):
                        fw.write(f"{record.id},{i}\n")


    config["post_qc_query"] = post_qc_query
    config["qc_fail"] = qc_fail

def get_package_data(cog_report,thisdir,config):
    reference_fasta = pkg_resources.resource_filename('civet', 'data/reference.fasta')
    outgroup_fasta = pkg_resources.resource_filename('civet', 'data/outgroup.fasta')
    polytomy_figure = pkg_resources.resource_filename('civet', 'data/polytomies.png')
    report_args = pkg_resources.resource_filename('civet', 'data/report_arguments.txt')
    footer_fig = pkg_resources.resource_filename('civet', 'data/footer.png')
    clean_locs = pkg_resources.resource_filename('civet', 'data/mapping_files/adm2_cleaning.csv')
    map_input_1 = pkg_resources.resource_filename('civet', 'data/mapping_files/gadm36_GBR_2.json')
    map_input_2 = pkg_resources.resource_filename('civet', 'data/mapping_files/channel_islands.json')  
    map_input_3 = pkg_resources.resource_filename('civet', 'data/mapping_files/NI_counties.geojson')  
    map_input_4 = pkg_resources.resource_filename('civet', 'data/mapping_files/Mainland_HBs_gapclosed_mapshaped_d3.json')
    map_input_5 = pkg_resources.resource_filename('civet', 'data/mapping_files/urban_areas_UK.geojson')
    map_input_6 = pkg_resources.resource_filename('civet', 'data/mapping_files/UK_outPC_coords.csv')
    spatial_translations_1 = pkg_resources.resource_filename('civet', 'data/mapping_files/HB_Translation.pkl')
    spatial_translations_2 = pkg_resources.resource_filename('civet', 'data/mapping_files/adm2_regions_to_coords.csv')
    config["reference_fasta"] = reference_fasta
    config["outgroup_fasta"] = outgroup_fasta
    config["polytomy_figure"] = polytomy_figure
    config["report_args"] = report_args
    config["footer"] = footer_fig
    
    config["clean_locs"] = clean_locs
    config["uk_map"] = map_input_1
    config["channels_map"] = map_input_2
    config["ni_map"] = map_input_3
    config["uk_map_d3"] = map_input_4
    config["urban_centres"] = map_input_5
    config["pc_file"] = map_input_6
    config["HB_translations"] = spatial_translations_1
    config["PC_translations"] = spatial_translations_2

    if cog_report:
        report_template = os.path.join(thisdir, 'scripts','COG_template.pmd')
    else:
        report_template = os.path.join(thisdir, 'scripts','civet_template.pmd')
    
    if not os.path.exists(report_template):
        sys.stderr.write(cyan(f'Error: cannot find report_template at {report_template}\n'))
        sys.exit(-1)
    config["report_template"] = report_template

def get_datadir(args_climb,args_datadir,remote,cwd,config):
    data_dir = ""
    if args_climb:
        data_dir = "/cephfs/covid/bham/civet-cat"
        if os.path.exists(data_dir):
            config["remote"] = False
            config["username"] = ""
        else:
            sys.stderr.write(cyan(f"Error: --CLIMB argument called, but CLIMB data path doesn't exist.\n"))
            sys.exit(-1)

    elif args_datadir:
        data_dir = os.path.join(cwd, args_datadir)
        
    if not remote:
        if not os.path.exists(data_dir):
            sys.stderr.write(cyan(f"Error: data directory not found at {data_dir}.\n")+ f"""The directory should contain the following files:\n\
    - cog_global_tree.nexus\n\
    - cog_metadata.csv\n\
    - cog_global_metadata.csv\n\
    - cog_global_alignment.fasta\n\
    - cog_alignment.fasta\n\n\
To run civet please either\n1) ssh into CLIMB and run with --CLIMB flag\n\
2) Run using `--remote-sync` flag and your CLIMB username specified e.g. `-uun climb-covid19-otoolexyz`\n\
3) Specify a local directory with the appropriate files\n\n""")
            sys.exit(-1)
            
        cog_metadata,cog_global_metadata = ("","")
        cog_seqs = ""
        cog_tree = ""
        
        cog_seqs = os.path.join(data_dir,"cog_alignment.fasta")
        
        cog_metadata = os.path.join(data_dir,"cog_metadata.csv")

        cog_global_metadata = os.path.join(data_dir,"cog_global_metadata.csv")
        cog_global_seqs= os.path.join(data_dir,"cog_global_alignment.fasta")

        cog_tree = os.path.join(data_dir,"cog_global_tree.nexus")

        if not os.path.isfile(cog_seqs) or not os.path.isfile(cog_global_seqs) or not os.path.isfile(cog_metadata) or not os.path.isfile(cog_global_metadata) or not os.path.isfile(cog_tree):
            sys.stderr.write(cyan(f"""Error: cannot find correct data files at {data_dir}\n""")+ f"""The directory should contain the following files:\n\
    - cog_global_tree.nexus\n\
    - cog_metadata.csv\n\
    - cog_global_metadata.csv\n\
    - cog_global_alignment.fasta\n\
    - cog_alignment.fasta\n\n\
To run civet please either\n1) ssh into CLIMB and run with --CLIMB flag\n\
2) Run using `--remote-sync` flag and your CLIMB username specified e.g. `-uun climb-covid19-otoolexyz`\n\
3) Specify a local directory with the appropriate files\n\n""")
            sys.exit(-1)
        else:
            config["cog_seqs"] = cog_seqs

            config["cog_metadata"] = cog_metadata

            config["cog_global_metadata"] = cog_global_metadata
            config["cog_global_seqs"] = cog_global_seqs
            config["cog_tree"] = cog_tree

            print("Found cog data:")
            print("    -",cog_seqs)
            print("    -",cog_metadata)
            print("    -",cog_global_metadata)
            print("    -",cog_tree,"\n")

    else:
        print("No data directory specified, will save data in civet-cat in current working directory")
        data_dir = cwd
        
    return data_dir
    
def get_remote_data(remote,uun,data_dir,args_datadir,args_climb,config):
    if remote:
        config["remote"]= True
        if uun:
            config["username"] = uun
        
            rsync_command = f"rsync -avzh {uun}@bham.covid19.climb.ac.uk:/cephfs/covid/bham/civet-cat '{data_dir}'"
            print(green(f"Syncing civet data to {data_dir}"))
            status = os.system(rsync_command)
            if status != 0:
                sys.stderr.write(cyan("Error: rsync command failed.\nCheck your user name is a valid CLIMB username e.g. climb-covid19-smithj\nAlso, check if you have access to CLIMB from this machine and are in the UK\n\n"))
                sys.exit(-1)
        else:
            rsync_command = f"rsync -avzh bham.covid19.climb.ac.uk:/cephfs/covid/bham/civet-cat '{data_dir}'"
            print(f"Syncing civet data to {data_dir}")
            status = os.system(rsync_command)
            if status != 0:
                sys.stderr.write(cyan("Error: rsync command failed.\nCheck your ssh is configured with Host bham.covid19.climb.ac.uk\nAlternatively enter your CLIMB username with -uun e.g. climb-covid19-smithj\nAlso, check if you have access to CLIMB from this machine and are in the UK\n\n"))
                sys.exit(-1)
        cog_metadata,cog_global_metadata = ("","")
        cog_seqs = ""
        cog_tree = ""

        cog_seqs = os.path.join(data_dir,"civet-cat","cog_alignment.fasta")
        cog_metadata = os.path.join(data_dir,"civet-cat","cog_metadata.csv")

        cog_global_metadata = os.path.join(data_dir,"civet-cat","cog_global_metadata.csv")
        cog_global_seqs= os.path.join(data_dir,"civet-cat","cog_global_alignment.fasta")

        cog_tree = os.path.join(data_dir,"civet-cat","cog_global_tree.nexus")

        config["cog_seqs"] = cog_seqs

        config["cog_metadata"] = cog_metadata
        config["cog_global_metadata"] = cog_global_metadata

        config["cog_global_seqs"] = cog_global_seqs
        config["cog_tree"] = cog_tree

        print("Found cog data:")
        print("    -",cog_seqs)
        print("    -",cog_metadata)
        print("    -",cog_global_metadata)
        print("    -",cog_tree,"\n")

    elif not args_datadir and not args_climb:
        sys.stderr.write(cyan("""Error: no way to find source data.\n\nTo run civet please either\n1) ssh into CLIMB and run with --CLIMB flag\n\
2) Run using `--remote-sync` flag and your CLIMB username specified e.g. `-uun climb-covid19-otoolexyz`\n\
3) Specify a local directory with the appropriate files on. The following files are required:\n\
- cog_global_tree.nexus\n\
- cog_metadata.csv\n\
- cog_global_metadata.csv\n\
- cog_global_alignment.fasta\n\
- cog_alignment.fasta\n\n"""))
        sys.exit(-1)

def get_dict_of_metadata_filters(to_parse, metadata):
    column_names =""
    query_dict = {}

    with open(metadata, newline="") as f:
        reader = csv.DictReader(f)
        column_names = reader.fieldnames
        
        # get each of the factors for the query
        for factor in to_parse:

            # eg country=Ireland 
            column_name,to_search = factor.split("=")

            # if the factor is in the metadata file add to the query dict
            if column_name in column_names:
                query_dict[column_name] = to_search

            else:
                # exit and print what the valid column names are
                cols = "\n- ".join(column_names)
                cols = cols + "\n"
                sys.stderr.write(cyan(f"""Error: `from-metadata` argument contains a column {column_name} that is not found in the metadata file supplied.
Columns that were found:\n{cols}"""))
                sys.exit(-1)
    return query_dict,column_names

def parse_date_range(metadata,column_name,to_search,rows_to_search):
    date_range = to_search.split(":")
    start_date = datetime.strptime(date_range[0], "%Y-%m-%d").date()
    end_date = datetime.strptime(date_range[1], "%Y-%m-%d").date()
    if rows_to_search == []:
        with open(metadata, newline="") as f:
            reader = csv.DictReader(f)
            c =0
            for row in reader:
                c +=1
                row_date = row[column_name]
                try:
                    check_date = datetime.strptime(row_date, "%Y-%m-%d").date()
                except:
                    sys.stderr.write(cyan(f"Error: Metadata field `{row_date}` [at column: {column_name}, row: {c}] contains unaccepted date format\Please use format `2020-05-19`\n"))
                    sys.exit(-1)
                if start_date <= check_date <= end_date:
                    rows_to_search.append((row,c))
    else:
        last_rows_to_search = rows_to_search
        new_rows_to_search = []
        for row,c in last_rows_to_search:
            row_date = row[column_name]
            try:
                check_date = datetime.strptime(row_date, "%Y-%m-%d").date()
            except:
                sys.stderr.write(cyan(f"Error: Metadata field `{row_date}` [at column: {column_name}, row: {c}] contains unaccepted date format\Please use format `YYYY-MM-DD`\n"))
                sys.exit(-1)
            if start_date <= check_date <= end_date:
                new_rows_to_search.append((row,c))
        
        rows_to_search = new_rows_to_search

def parse_general_field(metadata,column_name,to_search,rows_to_search):
    if rows_to_search == []:
        with open(metadata, newline="") as f:
            reader = csv.DictReader(f)
            c =0
            for row in reader:
                c +=1
                row_info = row[column_name]
                
                if row_info == to_search:
                    rows_to_search.append((row,c))
    else:
        last_rows_to_search = rows_to_search
        new_rows_to_search = []
        for row,c in last_rows_to_search:
            row_info = row[column_name]
            
            if row_info == to_search:
                new_rows_to_search.append((row,c))
        rows_to_search = new_rows_to_search

def generate_query_from_metadata(from_metadata, metadata, config):
    to_parse = ""
    if from_metadata:
        to_parse = from_metadata
        print(from_metadata)
    elif "from_metadata" in config:
        to_parse = config["from_metadata"]

    data_column = config["data_column"]
    config["input_column"] = data_column
    
    # checks if field in metadata file and adds to dict: query_dict[country]=Ireland for eg
    query_dict,column_names = get_dict_of_metadata_filters(to_parse, metadata)
    
    # if this is empty, for each column to search it'll open the whole file and search them
    # if it's not empty, it'll only search this list of rows
    rows_to_search = []
    
    for column_name in query_dict:
        
        to_search = query_dict[column_name]

        # assumes its a date range if it has a ':' and startswith 2020-, 2019- or 2021-
        if ':' in to_search:
            if to_search.startswith("2020-") or to_search.startswith("2019-") or to_search.startswith("2021-"):
                print(f"Date range detected: {to_search}")
                parse_date_range(metadata,column_name,to_search,rows_to_search)
        else:
            # parse by exact match 
            parse_general_field(metadata,column_name,to_search,rows_to_search)

    query = os.path.join(config["outdir"], "from_metadata_query.csv")

    with open(query,"w") as fw:
        writer = csv.DictWriter(fw, fieldnames=column_names,lineterminator='\n')
        writer.writeheader()
        count = 0

        query_ids = []
        for row,c in rows_to_search:
            writer.writerow(row)
            count +=1
            query_ids.append(row[data_column])

        if count == 0:
            sys.stderr.write(cyan(f"Error: No sequences meet the criteria defined with `--from-metadata`.\nExiting\n"))
            sys.exit(-1)
        print(green(f"Number of sequences matching defined query:") + f" {count}")
        if len(query_ids) < 100:
            for i in query_ids:
                print(f" - {i}")
    return query

def get_sequencing_centre_header(sequencing_centre_arg,config):
    
    sc_list = ["PHEC", 'LIVE', 'BIRM', 'PHWC', 'CAMB', 'NORW', 'GLAS', 'EDIN', 'SHEF',
                'EXET', 'NOTT', 'PORT', 'OXON', 'NORT', 'NIRE', 'GSTT', 'LOND', 'SANG',"NIRE"]

    if sequencing_centre_arg:
        sequencing_centre = sequencing_centre_arg
    elif "sequencing_centre" in config:
        sequencing_centre = config["sequencing_centre"]
    else:
        sequencing_centre = "DEFAULT"

    if sequencing_centre in sc_list or sequencing_centre == "DEFAULT":
        package_png = os.path.join("data","headers",f"{sequencing_centre}.png")
        sequencing_centre_source = pkg_resources.resource_filename('civet', package_png)
        print(green(f"Using header file from:") + f" {package_png}\n")
        config["sequencing_centre_source"] = sequencing_centre_source
        config["sequencing_centre_dest"] = os.path.join(config["outdir"],"figures",f"{sequencing_centre}.png")
        config["sequencing_centre_file"] = os.path.join(".","figures",f"{sequencing_centre}.png")
        config["sequencing_centre"] = sequencing_centre
    else:
        sc_string = "\n".join(sc_list)
        sys.stderr.write(cyan(f'Error: sequencing centre must be one of the following:\n{sc_string}\n'))
        sys.exit(-1)

def distance_config(distance, up_distance, down_distance, config):
    if distance:
        config["up_distance"] = distance
        config["down_dista nce"] = distance

    if up_distance:
        config["up_distance"] = up_distance

    if down_distance:
        config["down_distance"] = down_distance

    print(green(f"Extraction radius:\n")+f"\tUp distance: {up_distance}\n\tDown distance: {down_distance}\n")

def get_colours():
    colours = ['viridis', 'plasma', 'inferno', 'magma', 'cividis','Greys', 
            'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
            'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn',
            'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
            'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
            'hot', 'afmhot', 'gist_heat', 'copper',
            'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
            'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic',
            'twilight', 'twilight_shifted', 'hsv',
            'Pastel1', 'Pastel2', 'Paired', 'Accent',
            'Dark2', 'Set1', 'Set2', 'Set3',
            'tab10', 'tab20', 'tab20b', 'tab20c',
            'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
            'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg',
            'gist_rainbow', 'rainbow', 'jet', 'nipy_spectral', 'gist_ncar']
    return colours

def get_full_headers():
    #could open and parse the cog metadata here to make it flexible
    headers = ["central_sample_id", "biosample_source_id","sequence_name","secondary_identifier",
                "sample_date","epi_week","country","adm1","adm2","outer_postcode","is_surveillance","is_community",
                "is_hcw","is_travel_history","travel_history","lineage","lineage_support","uk_lineage","acc_lineage","del_lineage","phylotype"]

    return headers

def colour(text, text_colour):
    bold_text = 'bold' in text_colour
    text_colour = text_colour.replace('bold', '')
    underline_text = 'underline' in text_colour
    text_colour = text_colour.replace('underline', '')
    text_colour = text_colour.replace('_', '')
    text_colour = text_colour.replace(' ', '')
    text_colour = text_colour.lower()
    if 'red' in text_colour:
        coloured_text = RED
    elif 'green' in text_colour:
        coloured_text = GREEN
    elif 'yellow' in text_colour:
        coloured_text = YELLOW
    elif 'dim' in text_colour:
        coloured_text = DIM
    elif 'cyan' in text_colour:
        coloured_text = 'cyan'
    else:
        coloured_text = ''
    if bold_text:
        coloured_text += BOLD
    if underline_text:
        coloured_text += UNDERLINE
    if not coloured_text:
        return text
    coloured_text += text + END_FORMATTING
    return coloured_text

def red(text):
    return RED + text + END_FORMATTING

def cyan(text):
    return CYAN + text + END_FORMATTING

def green(text):
    return GREEN + text + END_FORMATTING

def yellow(text):
    return YELLOW + text + END_FORMATTING

def bold_underline(text):
    return BOLD + UNDERLINE + text + END_FORMATTING
