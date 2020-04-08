#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#############################################################
# File: main.py
# Created Date: 2020.4.26
# Author: Chen Xuanhong
# Email: chenxuanhongzju@outlook.com
# Last Modified:  Wednesday, 8th April 2020 1:28:53 am
# Modified By: Chen Xuanhong
# Copyright (c) 2019 Shanghai Jiao Tong University
#############################################################
import  platform
import  os
import  json
import  shutil
from    parameters import getParameters
from    utilities.reporter import Reporter
from    utilities.json_config import *
from    utilities.yaml_config import getConfigYaml
from    utilities.sshupload import fileUploaderClass

def create_dirs(sys_state):
    # the base dir
    if not os.path.exists(sys_state["logRootPath"]):
            os.makedirs(sys_state["logRootPath"])

    # create dirs
    sys_state["projectRoot"]        = os.path.join(sys_state["logRootPath"], sys_state["version"])
    if not os.path.exists(sys_state["projectRoot"]):
        os.makedirs(sys_state["projectRoot"])
    
    sys_state["projectSummary"]     = os.path.join(sys_state["projectRoot"], "summary")
    if not os.path.exists(sys_state["projectSummary"]):
        os.makedirs(sys_state["projectSummary"])

    sys_state["projectCheckpoints"] = os.path.join(sys_state["projectRoot"], "checkpoints")
    if not os.path.exists(sys_state["projectCheckpoints"]):
        os.makedirs(sys_state["projectCheckpoints"])

    sys_state["projectSamples"]     = os.path.join(sys_state["projectRoot"], "samples")
    if not os.path.exists(sys_state["projectSamples"]):
        os.makedirs(sys_state["projectSamples"])

    sys_state["projectScripts"]     = os.path.join(sys_state["projectRoot"], "scripts")
    if not os.path.exists(sys_state["projectScripts"]):
        os.makedirs(sys_state["projectScripts"])
    
    sys_state["reporterPath"] = os.path.join(sys_state["projectRoot"],sys_state["version"]+"_report")

def main(config):
    ignoreKey = [
        "dataloader_workers","logRootPath",
        "projectRoot","projectSummary","projectCheckpoints",
        "projectSamples","projectScripts","reporterPath",
        "useSpecifiedImg","dataset_path"
    ]
    sys_state = {}

    sys_state["dataloader_workers"] = config.dataloader_workers
    os.environ["CUDA_VISIBLE_DEVICES"] = str(config.cuda)
    # For fast training

    # read system environment path
    env_config = read_config('env/config.json')
    env_config = env_config["path"]
    
    # Train mode
    if config.mode == "train":
        
        sys_state["version"]                = config.version
        sys_state["experimentDescription"]  = config.experimentDescription
        sys_state["mode"]                   = config.mode
        # read training configurations
        ymal_config = getConfigYaml(os.path.join(env_config["trainConfigPath"], config.trainYaml))
        for item in ymal_config.items():
            sys_state[item[0]] = item[1]

        # create dirs
        sys_state["logRootPath"]        = env_config["trainLogRoot"]
        create_dirs(sys_state)
        
        # create reporter file
        reporter = Reporter(sys_state["reporterPath"])

        # save the config json
        config_json = os.path.join(sys_state["projectRoot"], env_config["configJsonName"])
        write_config(config_json, sys_state)

        # save the scripts
        # copy the scripts to the project dir 
        file1       = os.path.join(env_config["trainScriptsPath"], "trainer_%s.py"%sys_state["trainScriptName"])
        tgtfile1    = os.path.join(sys_state["projectScripts"], "trainer_%s.py"%sys_state["trainScriptName"])
        shutil.copyfile(file1,tgtfile1)

        file2       = os.path.join("./components", "%s.py"%sys_state["gScriptName"])
        tgtfile2    = os.path.join(sys_state["projectScripts"], "%s.py"%sys_state["gScriptName"])
        shutil.copyfile(file2,tgtfile2)

        file3       = os.path.join("./components", "%s.py"%sys_state["dScriptName"])
        tgtfile3    = os.path.join(sys_state["projectScripts"], "%s.py"%sys_state["dScriptName"])
        shutil.copyfile(file3,tgtfile3)

    elif config.mode == "finetune":
        sys_state["logRootPath"]    = env_config["trainLogRoot"]
        sys_state["version"]        = config.version
        sys_state["projectRoot"]    = os.path.join(sys_state["logRootPath"], sys_state["version"])

        config_json                 = os.path.join(sys_state["projectRoot"], env_config["configJsonName"])
        train_config                = read_config(config_json)
        for item in train_config.items():
            if item[0] in ignoreKey:
                pass
            else:
                sys_state[item[0]] = item[1]
        
        sys_state["mode"]           = config.mode
        create_dirs(sys_state)
        reporter = Reporter(sys_state["reporterPath"])
        
        
    elif config.mode == "test":
        sys_state["version"]        = config.testVersion
        sys_state["logRootPath"]    = env_config["trainLogRoot"]
        sys_state["nodeName"]       = config.nodeName
        sys_state["totalImg"]       = config.totalImg
        sys_state["useSpecifiedImg"]= config.useSpecifiedImg
        sys_state["checkpointStep"] = config.testCheckpointStep
        sys_state["testImgRoot"]    = config.testImgRoot

        sys_state["testSamples"]    = os.path.join(env_config["testLogRoot"], sys_state["version"] , "samples")
        if not os.path.exists(sys_state["testSamples"]):
            os.makedirs(sys_state["testSamples"])
        
        if config.useSpecifiedImg:  
            sys_state["useSpecifiedImg"]   = config.useSpecifiedImg       
        # Create dirs
        create_dirs(sys_state)
        config_json = os.path.join(sys_state["projectRoot"], env_config["configJsonName"])
        
        # Read model_config.json from remote machine
        if sys_state["nodeName"]!="localhost":
            print("ready to fetch the %s from the server!"%config_json)
            nodeinf     = read_config(env_config["remoteNodeInfo"])
            nodeinf     = nodeinf[sys_state["nodeName"]]
            uploader    = fileUploaderClass(nodeinf["ip"],nodeinf["user"],nodeinf["passwd"])
            remotebase  = os.path.join(nodeinf['basePath'],"train_logs",sys_state["version"]).replace('\\','/')
            # Get the config.json
            print("ready to get the config.json...")
            remoteFile  = os.path.join(remotebase, env_config["configJsonName"]).replace('\\','/')
            localFile   = config_json
            uploader.sshScpGet(remoteFile,localFile)
            print("success get the config file from server %s"%nodeinf['ip'])

        # Read model_config.json
        json_obj    = read_config(config_json)
        for item in json_obj.items():
            # sys_state[item[0]] = item[1]
            if item[0] in ignoreKey:
                pass
            else:
                sys_state[item[0]] = item[1]
        
        # get the dataset path
        sys_state["content"]= env_config["datasetPath"]["Place365_big"]
        sys_state["style"]  = env_config["datasetPath"]["WikiArt"]
            
        # Read scripts from remote machine
        if sys_state["nodeName"]!="localhost":
            # Get scripts
            remoteFile  = os.path.join(remotebase, "scripts", sys_state["gScriptName"]+".py").replace('\\','/')
            localFile   = os.path.join(sys_state["projectScripts"], sys_state["gScriptName"]+".py") 
            uploader.sshScpGet(remoteFile, localFile)
            print("Get the scripts:%s.py successfully"%sys_state["gScriptName"])
            # Get checkpoint of generator
            localFile   = os.path.join(sys_state["projectCheckpoints"], "%d_Generator.pth"%sys_state["checkpointStep"])
            if not os.path.exists(localFile):
                remoteFile  = os.path.join(remotebase, "checkpoints", "%d_Generator.pth"%sys_state["checkpointStep"]).replace('\\','/')
                uploader.sshScpGet(remoteFile, localFile, True)
                print("Get the %s file successfully"%("%d_Generator.pth"%sys_state["checkpointStep"]))
            else:
                print("%s file exists"%("%d_Generator.pth"%sys_state["checkpointStep"]))
        sys_state["ckp_name"]       = os.path.join(sys_state["projectCheckpoints"], "%d_Generator.pth"%sys_state["checkpointStep"])    
        # Get the test configurations
        sys_state["testScriptsName"]= config.testScriptsName
        sys_state["batchSize"]      = config.testBatchSize
        sys_state["totalImg"]       = config.totalImg
        sys_state["saveTestImg"]    = config.saveTestImg
        sys_state["com_base"]       = "train_logs.%s.scripts."%sys_state["version"]
        reporter = Reporter(sys_state["reporterPath"])
        
        # Display the test information
        moduleName  = "test_scripts.tester_" + sys_state["testScriptsName"]
        print("Start to run test script: {}".format(moduleName))
        print("Test version: %s"%sys_state["version"])
        print("Test Script Name: %s"%sys_state["testScriptsName"])
        print("Generator Script Name: %s"%sys_state["gScriptName"])
        # print("Discriminator Script Name: %s"%sys_state["stuScriptName"])
        print("Image Crop Size: %d"%sys_state["imCropSize"])
        package     = __import__(moduleName, fromlist=True)
        testerClass = getattr(package, 'Tester')
        tester      = testerClass(sys_state,reporter)
        tester.test()
    
    if config.mode == "train" or config.mode == "finetune":
        # get the dataset path
        sys_state["content"]= env_config["datasetPath"]["Place365_big"]
        sys_state["style"]  = env_config["datasetPath"]["WikiArt"]

        # display the training information
        moduleName  = "train_scripts.trainer_" + sys_state["trainScriptName"]
        print("Start to run training script: {}".format(moduleName))
        print("Traning version: %s"%sys_state["version"])
        print("Training Script Name: %s"%sys_state["trainScriptName"])
        print("Generator Script Name: %s"%sys_state["gScriptName"])
        print("Discriminator Script Name: %s"%sys_state["dScriptName"])
        # print("Image Size: %d"%sys_state["imsize"])
        print("Image Crop Size: %d"%sys_state["imCropSize"])
        print("D : G = %d : %d"%(sys_state["dStep"],sys_state["gStep"]))
        # Load the training script and start to train
        reporter.writeConfig(sys_state)
        package     = __import__(moduleName, fromlist=True)
        trainerClass= getattr(package, 'Trainer')
        trainer     = trainerClass(sys_state,reporter)
        trainer.train()

if __name__ == '__main__':
    config = getParameters()
    main(config)