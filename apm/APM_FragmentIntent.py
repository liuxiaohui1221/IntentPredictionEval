import sys
import os
import time, argparse
from bitmap import BitMap
import ParseConfigFile as parseConfig
import QueryParser as qp
import TupleIntent as ti
import re
import MINC_prepareJoinKeyPairs
from ParseConfigFile import getConfig
import random
import ReverseEnggQueries
import CFCosineSim_Parallel
#import MINC_QueryParser as MINC_QP

def seqIntentVectorFilesModifyCrawler(configDict):
    splitDir = getConfig(configDict['BIT_FRAGMENT_SEQ_SPLITS'])
    splitFileName = configDict['BIT_FRAGMENT_SEQ_SPLIT_NAME_FORMAT']
    numFiles = int(configDict['BIT_FRAGMENT_SEQ_SPLIT_THREADS'])
    sessionQueryDict = {} # key is session ID and value is line
    queryCount = 0
    prevSessName = None
    prevQueryVector = None
    #sessID = int(configDict['BIT_FRAGMENT_START_SESS_INDEX'])-1
    sessID = -1
    sessQueryID = float("-inf")
    queryLimit = int(configDict['QUERY_LIMIT'])
    for i in range(numFiles):
        fileNamePerThread = splitDir+"/"+splitFileName+str(i)
        with open(fileNamePerThread) as f:
            for line in f:
                line = line.strip()
                if len(line.split(";")) > 3:
                    line = removeExcessDelimiters(line)
                assert len(line.split(";")) == 3
                tokens = line.split(";")
                sessName = tokens[0].split(", ")[0].split(" ")[1]
                if sessName != prevSessName:
                    if sessID in sessionQueryDict and len(sessionQueryDict[sessID]) == 0:
                        del sessionQueryDict[sessID] # empty previous session
                    else:
                        sessID+=1
                    prevSessName = sessName
                    prevQueryVector = None
                if sessID >= int(configDict['BIT_FRAGMENT_START_SESS_INDEX']):
                    if sessID not in sessionQueryDict:
                        sessionQueryDict[sessID] = []
                        sessQueryID = 1 # since some query indices may be pruned in between
                    curQueryVector = BitMap.fromstring(tokens[2])
                    if prevQueryVector is None or CFCosineSim_Parallel.computeBitCosineSimilarity(curQueryVector, prevQueryVector) < 0.99:
                        newLine = "Session "+sessName+", Query "+str(sessQueryID) +";"+tokens[1]+";"+tokens[2]
                        sessionQueryDict[sessID].append(newLine)
                        sessQueryID += 1
                    prevQueryVector = curQueryVector
                    queryCount +=1
                    if queryLimit != 0 and queryCount > queryLimit: # 0 indicates no limit
                        break
                    if queryCount % 1000 == 0:
                        print("Query count so far: "+str(queryCount)+", len(sessionQueryDict): "+str(len(sessionQueryDict)))
    return sessionQueryDict


def seqIntentVectorFilesPruneCrawler(configDict):
    splitDir = getConfig(configDict['BIT_FRAGMENT_SEQ_SPLITS'])
    splitFileName = configDict['BIT_FRAGMENT_SEQ_SPLIT_NAME_FORMAT']
    numFiles = int(configDict['BIT_FRAGMENT_SEQ_SPLIT_THREADS'])
    sessionQueryDict = {} # key is session ID and value is line
    queryCount = 0
    prevSessName = None
    prevQueryVector = None
    repQuery = "False"
    #sessID = int(configDict['BIT_FRAGMENT_START_SESS_INDEX'])-1
    sessID = -1
    relSessID = -1
    queryLimit = int(configDict['QUERY_LIMIT'])
    for i in range(numFiles):
        fileNamePerThread = splitDir+"/"+splitFileName+str(i)
        with open(fileNamePerThread) as f:
            for line in f:
                line = line.strip()
                if len(line.split(";")) > 3:
                    line = removeExcessDelimiters(line)
                assert len(line.split(";")) == 3
                tokens = line.split(";")
                sessName = tokens[0].split(", ")[0].split(" ")[1]
                if sessName != prevSessName:
                    if repQuery == "True":
                        assert sessID in sessionQueryDict
                        del sessionQueryDict[sessID]
                        assert sessID not in sessionQueryDict
                        repQuery = "False"
                    else:
                        sessID+=1
                    prevSessName = sessName
                    prevQueryVector = None
                if sessID >= int(configDict['BIT_FRAGMENT_START_SESS_INDEX']):
                    if sessID not in sessionQueryDict:
                        sessionQueryDict[sessID] = []
                    sessionQueryDict[sessID].append(line)
                    curQueryVector = BitMap.fromstring(tokens[2])
                    if prevQueryVector is not None and CFCosineSim_Parallel.computeBitCosineSimilarity(curQueryVector,
                                                                                                       prevQueryVector) >= 0.99:
                        repQuery = "True"
                    prevQueryVector = curQueryVector
                    queryCount +=1
                    if queryLimit != 0 and queryCount > queryLimit: # 0 indicates no limit
                        break
                    if queryCount % 1000 == 0:
                        print("Query count so far: " + str(queryCount) + ", len(sessionQueryDict): " + str(
                            len(sessionQueryDict)))
    return sessionQueryDict

def seqIntentVectorFilesKeepCrawler(configDict):
    # 获取配置文件中的文件名格式
    splitFileName = configDict['BIT_FRAGMENT_SEQ_SPLIT_NAME_FORMAT']
    # 获取当前文件所在的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 初始化文件数量
    numFiles = 1
    sessionQueryDict = {} # key is session ID and value is line
    queryCount = 0
    prevSessName = {}
    #sessID = int(configDict['BIT_FRAGMENT_START_SESS_INDEX'])-1
    sessID = -1
    relSessID = -1
    queryLimit = int(configDict['QUERY_LIMIT'])
    fileNamePerThread = os.path.join(current_dir,"../"+splitFileName)
    print(fileNamePerThread)
    with open(fileNamePerThread, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if len(line.split(";")) > 3:
                line = removeExcessDelimiters(line)
            if len(line.split(";"))>3:
                tokens = line.split(";")
            assert len(line.split(";")) == 3
            tokens = line.split(";")
            sessName = tokens[0].split(", ")[0].split(" ")[1]
            if sessName in prevSessName:
                sessID=prevSessName[sessName]
            else:
                sessID=int(sessName)
                prevSessName[sessName]=sessID
            if sessID >= int(configDict['BIT_FRAGMENT_START_SESS_INDEX']):
                if sessID not in sessionQueryDict:
                    sessionQueryDict[sessID] = []
                sessionQueryDict[sessID].append(line)
                queryCount +=1
                if queryLimit != 0 and queryCount > queryLimit: # 0 indicates no limit
                    break
                if queryCount % 10000 == 0:
                    print("Query count so far: "+str(queryCount)+", len(sessionQueryDict): "+str(len(sessionQueryDict)))
    return sessionQueryDict

def concatenateSeqIntentVectorFiles(configDict):
    splitDir = getConfig(configDict['BIT_FRAGMENT_SEQ_SPLITS'])
    splitFileName = configDict['BIT_FRAGMENT_SEQ_SPLIT_NAME_FORMAT']
    numFiles = int(configDict['BIT_FRAGMENT_SEQ_SPLIT_THREADS'])
    sessionQueryDict = {} # key is session ID and value is line
    queryCount = 0
    prevSessName = None
    sessID = int(configDict['BIT_FRAGMENT_START_SESS_INDEX'])-1
    queryLimit = int(configDict['QUERY_LIMIT'])
    for i in range(numFiles):
        fileNamePerThread = splitDir+"/"+splitFileName+str(i)
        with open(fileNamePerThread) as f:
            for line in f:
                line = line.strip()
                if len(line.split(";")) > 3:
                    line = removeExcessDelimiters(line)
                assert len(line.split(";")) == 3
                tokens = line.split(";")
                sessName = tokens[0].split(", ")[0].split(" ")[1]
                if sessName != prevSessName:
                    sessID+=1
                    prevSessName = sessName
                if sessID not in sessionQueryDict:
                    sessionQueryDict[sessID] = []
                sessionQueryDict[sessID].append(line)
                queryCount +=1
                if queryLimit != 0 and queryCount > queryLimit:  # 0 indicates no limit
                    break
                if queryCount % 10000 == 0:
                    print("Query count so far: "+str(queryCount))
    return sessionQueryDict

def createQuerySessions(rootApmDir,sessionQueryDict, configDict):
    sessQueryFile = os.path.join(rootApmDir,"../"+configDict['QUERYSESSIONS'])
    try:
        os.remove(sessQueryFile)
    except OSError:
        pass
    for sessID in sessionQueryDict:
        output_str = "Session "+str(sessID)+";"
        for i in range(len(sessionQueryDict[sessID])):
            output_str = output_str + sessionQueryDict[sessID][i].split(";")[1].split(":")[1]+";"
        ti.appendToFile(sessQueryFile, output_str)

def removeExcessDelimiters(sessQueryIntent):
    tokens = sessQueryIntent.split(";")
    ret_str = tokens[0]+";"
    for i in range(1,len(tokens)-1):
        if i == 1:
            ret_str = ret_str+tokens[i]
        else:
            ret_str = ret_str+","+tokens[i]
    ret_str = ret_str + ";"+tokens[len(tokens)-1]
    return ret_str

def tryDeletionIfExists(fileName):
    try:
        os.remove(fileName)
    except OSError:
        pass
    return


def getConfigPath(param):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "../"+param)


def createSingularityIntentVectors(sessionQueryDict, configDict):
    # 获取intentFile、concurrentFile、tableIntentFile的路径
    intentFile = getConfigPath(configDict['BIT_FRAGMENT_INTENT_SESSIONS'])
    concurrentFile = getConfigPath(configDict['CONCURRENT_QUERY_SESSIONS'])
    tableIntentFile = getConfigPath(configDict['BIT_FRAGMENT_TABLE_INTENT_SESSIONS'])
    # 读取schemaDicts
    schemaDicts = ReverseEnggQueries.readSchemaDicts(configDict)
    # 删除intentFile、concurrentFile、tableIntentFile
    tryDeletionIfExists(intentFile)
    tryDeletionIfExists(concurrentFile)
    tryDeletionIfExists(tableIntentFile)
    # 初始化queryCount、queryIndex、absCount
    queryCount = 0
    queryIndex = 0
    absCount = 0
    # sessionQueryDict key为sessionid, value为list,
    # list中每个元素为query line: "Session 1, Query 1;original query;query bit vector"
    numSessions = len(sessionQueryDict)
    # 当sessionQueryDict不为空时，循环
    while len(sessionQueryDict)!=0:
        # 获取sessionQueryDict的key列表
        keyList = list(sessionQueryDict.keys())
        # 随机打乱session顺序
        random.shuffle(keyList)
        # queryIndex递增
        queryIndex += 1
        # 遍历keyList
        for sessIndex in keyList:
            # print("size:", len(sessionQueryDict[sessIndex]))
            # 获取sessQueryIntent
            sessQueryIntent = sessionQueryDict[sessIndex][0]
            # 从sessionQueryDict中移除sessQueryIntent
            sessionQueryDict[sessIndex].remove(sessQueryIntent)
            # 如果sessionQueryDict[sessIndex]为空，则删除sessIndex
            if len(sessionQueryDict[sessIndex]) == 0:
                del sessionQueryDict[sessIndex]
            #queryIndexRec = sessQueryIntent.split(";")[0].split(", ")[1].split(" ")[1]
            #if queryIndexRec != str(queryIndex):
                #print "queryIndexRec != queryIndex !!"
            #assert queryIndexRec == str(queryIndex)
            # 将sessQueryIntent按";"分割
            tokens = sessQueryIntent.split(";")
            print("query intent:",len(tokens[2]))
            # 断言tokens的长度为3
            assert len(tokens) == 3
            # 断言queryCount>=0
            assert queryCount>=0
            # 如果queryCount为0，则初始化output_str、output_table_str、conc_str
            if queryCount == 0:
                output_str = "Session " + str(sessIndex) + ", Query " + str(queryIndex) + ";" + tokens[1] + ";" + tokens[2]
                output_table_str = "Session " + str(sessIndex) + ", Query " + str(queryIndex) + ";" + tokens[1] + ";" + \
                             tokens[2][schemaDicts.tableStartBitIndex:schemaDicts.tableStartBitIndex+schemaDicts.tableBitMapSize]
                conc_str = "Session " + str(sessIndex) + ", Query " + str(queryIndex) + ";" + tokens[1].split(":")[1]
            else:
                # 否则，将output_str、output_table_str、conc_str追加
                output_str += "\nSession " + str(sessIndex) + ", Query " + str(queryIndex) + ";" + tokens[1] + ";" + tokens[2]
                output_table_str += "\nSession " + str(sessIndex) + ", Query " + str(queryIndex) + ";" + tokens[1] + ";" + \
                                   tokens[2][schemaDicts.tableStartBitIndex:schemaDicts.tableStartBitIndex + schemaDicts.tableBitMapSize]
                conc_str += "\nSession " + str(sessIndex) + ", Query " + str(queryIndex) + ";" + tokens[1].split(":")[1]
            # queryCount递增
            queryCount += 1
            # absCount递增
            absCount+=1
            # 如果queryCount % 100 == 0，则将output_str、conc_str、output_table_str写入文件
            if queryCount % 100 == 0:
                ti.appendToFile(intentFile, output_str)
                ti.appendToFile(concurrentFile, conc_str)
                ti.appendToFile(tableIntentFile, output_table_str)
                # queryCount置为0
                queryCount = 0
            # 如果absCount % 10000 == 0，则打印信息
            if absCount % 10000 == 0:
                print("appended Session " + str(sessIndex) + ", Query " + str(queryIndex) + ", absQueryCount: " + str(absCount))
    # 如果queryCount > 0，则将output_str、conc_str、output_table_str写入文件
    if queryCount > 0:
        ti.appendToFile(intentFile, output_str)
        ti.appendToFile(concurrentFile, conc_str)
        ti.appendToFile(tableIntentFile, output_table_str)
    # 打印信息
    print("Created intent vectors for # Sessions: "+str(numSessions)+" and # Queries: "+str(absCount))


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # configDict = parseConfig.parseConfigFile(os.path.join(current_dir,
    #                                                       "../config/APM_Table_Realtime_FragmentQueries_Keep_configFile.txt"))
    parser = argparse.ArgumentParser()
    parser.add_argument("-config", help="Config parameters file", type=str, required=True)
    args = parser.parse_args()
    configDict = parseConfig.parseConfigFile(args.config)
    assert configDict["BIT_OR_WEIGHTED"] == "BIT"
    fragmentIntentSessionsFile = os.path.join(current_dir,"../"+getConfig(configDict['BIT_FRAGMENT_INTENT_SESSIONS']))
    try:
        print("Deleting existing file: "+fragmentIntentSessionsFile)
        os.remove(fragmentIntentSessionsFile)
    except OSError:
        pass
    assert configDict['KEEP_PRUNE_MODIFY_CRAWLER_SESS'] == "KEEP" or \
           configDict['KEEP_PRUNE_MODIFY_CRAWLER_SESS'] == "PRUNE" or \
           configDict['KEEP_PRUNE_MODIFY_CRAWLER_SESS'] == "MODIFY"
    if configDict['KEEP_PRUNE_MODIFY_CRAWLER_SESS'] == "KEEP":
        sessionQueryDict = seqIntentVectorFilesKeepCrawler(configDict)
    elif configDict['KEEP_PRUNE_MODIFY_CRAWLER_SESS'] == "PRUNE":
        sessionQueryDict = seqIntentVectorFilesPruneCrawler(configDict)
    elif configDict['KEEP_PRUNE_MODIFY_CRAWLER_SESS'] == "MODIFY":
        sessionQueryDict = seqIntentVectorFilesModifyCrawler(configDict)
    createQuerySessions(current_dir, sessionQueryDict, configDict)
    createSingularityIntentVectors(sessionQueryDict, configDict)