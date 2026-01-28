import os
import subprocess
import maya.cmds as cmds
import maya.api.OpenMaya as om2
import maya.api.OpenMayaUI as omui
import maya.OpenMayaUI as OpenMayaUI
import maya.mel as mel

try:
    from PySide2 import QtWidgets,QtGui,QtCore
    qaction = QtWidgets.QAction

except:
    from PySide6 import QtWidgets,QtGui,QtCore
    qaction = QtGui.QAction

##--------------------------------------------------------
##--------------------------------------------------------

def saveDictOptionVar(toolName,optionDict):
    optionString= ""

    for key in optionDict:
        if optionString != "":
            optionString += ";"
    
        optionString += key + ";" + str(optionDict[key])

    cmds.optionVar(stringValue = [toolName,optionString])


def readDictOptionVar(toolName):
    optionString = ""
    if cmds.optionVar(exists = toolName):
        optionString = cmds.optionVar(q = toolName)
    
    optionDict = {}

    optionArray = optionString.split(";")
    if len(optionArray) > 1:
        for i in range(0,len(optionArray),2):
            optionDict[optionArray[i]] = optionArray[i+1]

    return optionDict

class ApplyFunc(object):
    def __init__(self, func, *args, **kwargs):
        self.__func = func
        self.__args = args
        self.__kwargs = kwargs
                        
    def __call__(self, *args, **kwargs):
        error = None        
        try:
            cmds.undoInfo(openChunk =True)

            self.__func(*self.__args, **self.__kwargs)			
                        
        except Exception as e:
            import traceback
            traceback.print_exc()

        finally:            
            cmds.undoInfo(closeChunk =True)
##--------------------------------------------------------
## MARK: scene info
##--------------------------------------------------------
def getDagNode(target):
    try:
        sellist = om.MGlobal.getSelectionListByName(target)
        return sellist.getDagPath(0)
    except:
        return None
    
def getFullPathName(target):
    if type(getDagNode(target)) != om.MDagPath:
        return target

    return om.MFnDagNode(getDagNode(target).node()).fullPathName()

def getTransformNode(targets,fullpath = False):
    transfromNodes = []
    
    for target in targets:
        nodeTypes = cmds.nodeType(target,inherited = True)
        transfromNode = None
        if "transform" in nodeTypes:
            transfromNode = target
        
        elif "shape" in nodeTypes:
            parent = cmds.listRelatives(target, p =True,f=fullpath)[0]
            transfromNode = parent

        if transfromNode not in transfromNodes:
            transfromNodes.append(transfromNode)
    
    return transfromNodes

def getIKJointChain(ikHandle,fullpath):
    ikHandleDag = getDagNode(ikHandle)    
    ikHandleDnFn = om.MFnDependencyNode(ikHandleDag.node())
    
    if fullpath:
        startJoint = om.MFnDagNode(ikHandleDnFn.findPlug('startJoint', False).source().node()).fullPathName()
        effector = om.MFnDagNode(ikHandleDnFn.findPlug('endEffector', False).source().node()).fullPathName()

        effectorDag = getDagNode(effector)
        effectorDnFn = om.MFnDependencyNode(effectorDag.node())
        endJoint = om.MFnDagNode(effectorDnFn.findPlug('offsetParentMatrix', False).source().node()).fullPathName()
    
    else:
        startJoint = om.MFnDagNode(ikHandleDnFn.findPlug('startJoint', False).source().node()).name()
        effector = om.MFnDagNode(ikHandleDnFn.findPlug('endEffector', False).source().node()).name()

        effectorDag = getDagNode(effector)
        effectorDnFn = om.MFnDependencyNode(effectorDag.node())
        endJoint = om.MFnDagNode(effectorDnFn.findPlug('offsetParentMatrix', False).source().node()).name()

    jointChain = getCurHierarchy(endJoint,startJoint,fullpath)

    return jointChain

def subIgnorTypeNodes(nodes,ignorNodeTypes,topNode,fullpath):
        for ignorType in ignorNodeTypes:
            nodes = list(set(nodes) - set(listTypeNodes(ignorType,topNode,fullpath)))

        return nodes

def listTypeNodes(nodeType,topNode = None, fullpath = False,ignorNodeTypes =[],nameSpace = None):
    defaultNodes = cmds.ls(defaultNodes =True, l= fullpath)

    if fullpath:
        topNode = getFullPathName(topNode)
    
    nodes = []    
    if nodeType == "transform":
        nodes = cmds.ls(type = nodeType, l= fullpath) or []

    elif nodeType == "noShapeTransform":
        nodes = listTypeNodes("transform",topNode,fullpath)
        
        shapes = cmds.ls(shapes =True, l = fullpath)        
        removeNodes = getTransformNode(shapes,fullpath)
        nodes = list(set(nodes) - set(removeNodes))

    elif nodeType == "locator":
        nodes = cmds.ls(type = nodeType, l= fullpath) or []
        nodes = getTransformNode(nodes,fullpath)
        
    elif nodeType == "joint":
        nodes = cmds.ls(type = nodeType, l= fullpath) or []

    elif nodeType == "IKJoints":
        ikHandles = cmds.ls(type = "ikHandle", l= fullpath) or []
        
        for ikHandle in ikHandles:
            jointChain = getIKJointChain(ikHandle,fullpath)
            nodes.extend(jointChain)

    elif nodeType == "constraint":
        nodes = cmds.ls(type = nodeType, l= fullpath) or []

    elif nodeType == "mesh" or nodeType == "nurbsCurve" or nodeType == "nurbsSurface":
        nodes = cmds.ls(type = nodeType, l= fullpath) or []
        nodes = getTransformNode(nodes,fullpath)

    elif nodeType == "camera":
        nodes = cmds.ls(type = nodeType, l= fullpath) or []
        nodes = getTransformNode(nodes,fullpath)

    elif nodeType == "light":
        nodes = cmds.ls(type = nodeType, l= fullpath) or []
        nodes = getTransformNode(nodes,fullpath)

    else:
        nodes = cmds.ls(type = nodeType, l= fullpath) or []

    if topNode != None:
        allHierarchy = cmds.listRelatives(topNode,ad =True,f=fullpath) or []
        allHierarchy.append(topNode)
        nodes = list(set(nodes) & set(allHierarchy))

    nodes = subIgnorTypeNodes(nodes,ignorNodeTypes,topNode,fullpath)
    nodes = list(set(nodes) - set(defaultNodes))

    if nameSpace != None:
        tempNodes= []
        for node in nodes:
            if node.startswith(nameSpace +":"):
                tempNodes.append(node)
        nodes = tempNodes
    return nodes

def getFrameRange(rangeFrom):
    if rangeFrom == "animation":
        start = cmds.playbackOptions(q =True, animationStartTime=True)
        end = cmds.playbackOptions(q =True, animationEndTime=True)

    elif rangeFrom == "timeSlider":
        start = cmds.playbackOptions(q =True, minTime=True)
        end = cmds.playbackOptions(q =True, maxTime=True)

    elif rangeFrom == "renderSetting":
        start = cmds.getAttr("defaultRenderGlobals.startFrame")
        end = cmds.getAttr("defaultRenderGlobals.endFrame")

    elif rangeFrom == "selection":
        aPlayBackSliderPython = mel.eval('$tmpVar=$gPlayBackSlider')
        s_e = cmds.timeControl(aPlayBackSliderPython, q=True, rangeArray=True)
        start = s_e[0]
        end = s_e[1]

    return start,end

def getCamAttrDict():
    start,end = getFrameRange("animation")
    CAMATTRS = [
        {"attrName":"startFrame","type":"double","default":start, "min":-10000,"max":10000},
        {"attrName":"endFrame","type":"double","default":end, "min":-10000,"max":10000},
        # {"attrName":"resolutionW","type":"long","default":cmds.getAttr("defaultResolution.width"), "min":1,"max":100000},
        # {"attrName":"resolutionH","type":"long","default":cmds.getAttr("defaultResolution.height"), "min":1,"max":100000},
        {"attrName":"playblast","type":"bool","default":False},
    ]

    return CAMATTRS

def setCameraInfo(node,valueDict):
    for attrDict in getCamAttrDict():
        attrName = attrDict["attrName"]
        attrType = attrDict["type"]
        

        if valueDict == None:
            value = attrDict["default"]

        elif attrName not in list(valueDict.keys()):
            continue
        
        if valueDict != None and attrName in list(valueDict.keys()):
            value = valueDict[attrName]


        if cmds.objExists(node+ "."+ attrName) == False:
            if attrDict["type"] == "double":
                value = float(value)

            elif attrDict["type"] == "long":
                value = int(value)

            elif attrDict["type"] == "bool":
                value = bool(value)

            cmds.addAttr(node, at = attrType, ln = attrName,dv = value)

        cmds.setAttr(node + "." + attrName,value)

def createCameraInfoNode(rootsetName,cameraname):

    if cmds.objExists(rootsetName) == False:
        cmds.sets(name = rootsetName,empty =True)

    if cmds.objExists(cameraname + "_infoSet",) == False:
        cmds.sets(name = cameraname + "_infoSet",empty=True)
        cmds.sets(cameraname + "_infoSet",forceElement = rootsetName)
        setCameraInfo(cameraname + "_infoSet",None)

    return cameraname + "_infoSet"

def findAttrInfo(attrName):
    for attrDict in getCamAttrDict():
        if attrDict["attrName"] == attrName:
            return attrDict
    
    return {}

def getCameraInfo(rootsetName,cameraname):
    node = createCameraInfoNode(rootsetName,cameraname)
    valueDict = {}

    for attrDict in getCamAttrDict():
        attrName = attrDict["attrName"]

        if cmds.objExists(node+ "."+ attrName) == False:
            value = attrDict["default"]
        else:
            value = cmds.getAttr(node + "." +attrName)

        valueDict[attrName] = value
    
    return valueDict

def getPlayblastCam(rootsetName):

    enabledCameras = []

    if cmds.objExists(rootsetName) == False:
        return []
    
    cameraSets = cmds.sets(rootsetName,q=True)

    for cameraSet in cameraSets:
        if cmds.objExists(cameraSet + ".playblast"):
            if cmds.getAttr(cameraSet + ".playblast"):
                enabledCameras.append(cameraSet.replace("_infoSet",""))

    return enabledCameras


def getCurSceneName():
    fullPath = cmds.file(q=True, sn=True)
    fileName = os.path.basename(fullPath)
    filePath = os.path.dirname(fullPath)

    if filePath != "":
        filePath += "/"
        
    fileNameBody, extension = os.path.splitext(fileName)
    
    return filePath,fileNameBody,extension

def generateOutputName(camera,fileNameFormat):
    filePath,fileNameBody,extension = getCurSceneName()

    fileNameParts = {
                        "scene":fileNameBody,
                        "camera":camera
                        # "version":str(version).zfill(4)
    }
    fileName = fileNameFormat.format(**fileNameParts)
    return fileName

def checkNeedSave():
    fileCheckState = cmds.file(q=True, modified=True)
    curOpen = cmds.file(q=True, sn=True)

    if curOpen == "":
        curOpen = "untitled"

    if fileCheckState:
        mel.eval("checkForUnknownNodes();")
        saved = mel.eval("saveChanges(\"\");")

        if saved == 0:
            return False

    return True

##----------------------------------------------------------------------------------
##MARK:playblast
##----------------------------------------------------------------------------------
def createShotNode(cameraname,cutName,timeRange):    
    shotNode = cmds.shot(cutName, startTime=timeRange[0], endTime = timeRange[1],sequenceStartTime = 1,currentCamera = cameraname)

    if cmds.objExists(cameraname + ".startFrame"):
        cmds.connectAttr(cameraname + ".startFrame",shotNode + ".startFrame")
        cmds.connectAttr(cameraname + ".endFrame",shotNode + ".endFrame")

    return shotNode

def getFrames(startFrame,endFrame,byFrame):
    frames = []
    for i in range(int(startFrame),int(endFrame) +1,int(byFrame)):
        frames.append(i)

    return frames

def excutePlayBlast(viewItemOption,camera,outputPath,outputFormat,timeRange,resolution,frameNumberOffset,nodes =None,panel = None):
    cmds.select(cl = True)
    window = None
    
    if panel == None:
        window,panel = createTmpView()
        cmds.modelEditor(panel, edit=True, **viewItemOption)

    cmds.modelEditor(panel, edit=True, camera=camera)

    if nodes != None:
        setIsolateView(panel,nodes)

    compressionDict = {
                            "png":["png","image"],
                            "jpg":["jpg","image"],
                            "avi":["none","movie"]
                        }
    
    outputPath = outputPath.replace("//","/")

    if frameNumberOffset:
        cmds.playblast(
                    filename =          outputPath,
                    forceOverwrite =    True,
                    format =            compressionDict[outputFormat][1],
                    compression =       compressionDict[outputFormat][0],
                    sequenceTime =      True,
                    clearCache =        1,
                    viewer =            False,
                    showOrnaments =     True,
                    offScreen =         True,
                    fp = 4, 
                    percent = 100,
                    quality = 100,
                    startTime =         timeRange[0],
                    endTime =           timeRange[1],
                    widthHeight =       resolution,
                    editorPanelName =   panel,                    
                )
    else:
        cmds.playblast(
                    filename =          outputPath,
                    forceOverwrite =    True,
                    format =            compressionDict[outputFormat][1],
                    compression =       compressionDict[outputFormat][0],
                    sequenceTime =      0,
                    clearCache =        1,
                    viewer =            False,
                    showOrnaments =     True,
                    offScreen =         True,
                    fp = 4, 
                    percent = 100,
                    quality = 100,
                    startTime =         timeRange[0],
                    endTime =           timeRange[1],
                    widthHeight =       resolution,
                    editorPanelName =   panel,                    
                )

    cmds.isolateSelect(panel,state = False)

    if window != None:
        cmds.deleteUI(window)

def playBlastProcess(camera,viewItemOption,showHUDs,outputPath,outputFormat,timeRange,resolution,frameNumberOffset):
    displayResolution,overscan,curHUDs = getCurViewSetting(camera)
    prepareViewSetting(camera,showHUDs["resolutionGate"],showHUDs,viewItemOption["headsUpDisplay"])

    if frameNumberOffset:        
        if cmds.objExists("playblastTmpSeq"):
            cmds.delete("playblastTmpSeq")

        shotNode = createShotNode(camera,"playblastTmpSeq",timeRange)
        timeRange[0] = cmds.getAttr(shotNode + ".sequenceStartFrame")
        timeRange[1] = cmds.getAttr(shotNode + ".sequenceEndFrame")

    try:
        excutePlayBlast(viewItemOption,camera,outputPath,outputFormat,timeRange,resolution,frameNumberOffset,nodes =None,panel = None)
    except:
        pass
    
    if cmds.objExists("playblastTmpSeq"):
        cmds.delete("playblastTmpSeq")

    restoreViewSetting(camera,displayResolution,overscan,curHUDs)

##----------------------------------------------------------------------------------
##MARK:viewPort
##----------------------------------------------------------------------------------

def getCurViewPanel():
    return OpenMayaUI.MQtUtil.fullName(int(omui.M3dView.active3dView().widget())).split("|")[-2]

def changeView(cameraName,viewPort):
    if cmds.objExists(cameraName) == False:
        return

    if viewPort == None:
        viewPort = getCurViewPanel()

    cmds.modelEditor(viewPort, edit=True, camera=cameraName)
    cmds.refresh()

def getView(panelName):    
    if cmds.modelPanel(panelName, exists =True) == False:
        return None

    if panelName not in cmds.getPanel(visiblePanels=True) or []:
        return None
    
    return omui.M3dView.getM3dViewFromModelPanel(panelName)
                
def setIsolateView(panelName,nodes):
    cmds.isolateSelect(panelName,state = False)        
    cmds.isolateSelect(panelName,state = True)
    
    for node in nodes:
        cmds.isolateSelect(panelName,addDagObject = node)

def createTmpView():
    if cmds.window('playblastTmp',q=True, ex =True):
        cmds.deleteUI('playblastTmp')

    window = cmds.window('playblastTmp')
    mainLayout = cmds.formLayout(window)
    panel = cmds.modelEditor()
    cmds.formLayout(mainLayout, e=True,
                                attachForm=[(panel, "top", 0),(panel, "left", 0), 
                                    (panel, "bottom", 0), (panel, "right", 0)]) 
    cmds.showWindow(window)
    return window,panel

def getCurHUDItems():
    showItems = []
    items = cmds.headsUpDisplay(listHeadsUpDisplays =True)
    for item in items:
        if cmds.headsUpDisplay(item, q = True, vis = True):
            showItems.append(item)

    return showItems

def hideAllHUDTtems():
    items = cmds.headsUpDisplay(listHeadsUpDisplays =True)

    for item in items:
        cmds.headsUpDisplay(item, e = True, vis = False) 

def setHUDItems(setNames):
    HUDDict = {
            "objectDetails":            ["HUDObjDetBackfaces","HUDObjDetSmoothness","HUDObjDetInstance","HUDObjDetDispLayer","HUDObjDetDistFromCm","HUDObjDetNumSelObjs"],
            "polyCount":                ["HUDPolyCountVerts","HUDPolyCountEdges","HUDPolyCountFaces","HUDPolyCountTriangles","HUDPolyCountUVs"],
            "particleCount":            ["HUDParticleCount"],
            "subdDetails":              ["HUDSubdLevel","HUDSubdMode"],
            "viewportRenderer":         ["HUDViewportRenderer"],
            "symmetry":                 ["HUDSymmetry"],
            "capsLock":                 ["HUDCapsLock"],
            "cameraNames":              ["HUDCameraNames"],
            "focalLength":              ["HUDFocalLength"],
            "frameRate":                ["HUDFrameRate"],
            "materialLoadingDetails":   ["HUDLoadingTextures","HUDLoadingMaterials"],
            "currentFrame":             ["HUDCurrentFrame"],
            "sceneTimecode":            ["HUDSceneTimecode"],
            "currentContainer":         ["HUDCurrentContainer"],
            "viewAxis":                 ["HUDViewAxis"],
            "HikDetails":               ["HUDHikKeyingMode"],
            "selectDetails":            ["HUDSoftSelectState"],
            "animationDetails":         ["HUDIKSolverState","HUDCurrentCharacter","HUDPlaybackSpeed","HUDSoftSelectState"],
            "toolMessage":              ["HUDSoftSelectState"],
            "XGenHUD":                  ["HUDSoftSelectState","HUDXGenSplinesCount","HUDXGenGPUMemory"],
            "evaluationManagerHUD":     ["HUDGPUOverride","HUDEMState","HUDEvaluation","HUDSoftSelectState"]
    }

    for key in setNames:
        if key not in list(HUDDict.keys()):
            continue

        for item in HUDDict[key]:
            if cmds.headsUpDisplay(item, exists = True) == False: 
                continue

            cmds.headsUpDisplay(item, e = True, vis = True) 

def getCurViewSetting(camera):
    displayResolution = cmds.getAttr(camera + ".displayResolution")
    overscan = cmds.getAttr(camera + ".overscan")
    curHUDs = getCurHUDItems()
    return displayResolution,overscan,curHUDs

def prepareViewSetting(camera,resolutionGate,showHUDs,headsUpDisplay):
    displayResolution,overscan,curHUDs = getCurViewSetting(camera)

    hideAllHUDTtems()

    showHUDItems = []

    for HUDItem in list(showHUDs.keys()):
        if showHUDs[HUDItem]:
            showHUDItems.append(HUDItem)

    if headsUpDisplay ==False:
        cmds.setAttr(camera + ".displayResolution",False)
        cmds.setAttr(camera + ".overscan",1.0)

    elif headsUpDisplay == True and resolutionGate == False:
        cmds.setAttr(camera + ".displayResolution",False)
        cmds.setAttr(camera + ".overscan",1.0)

    if resolutionGate == True and displayResolution == False:        
        cmds.setAttr(camera + ".displayResolution",True)
        cmds.setAttr(camera + ".overscan",1.3)

    setHUDItems(showHUDItems)

def restoreViewSetting(camera,displayResolution,overscan,curHUDs):
    cmds.setAttr(camera + ".displayResolution",displayResolution)
    cmds.setAttr(camera + ".overscan",overscan)
    hideAllHUDTtems()
    setHUDItems(curHUDs)

##----------------------------------------------------------------------------------
##MARK:GUI
##----------------------------------------------------------------------------------
def getTopLevelWidget(name):
    for widget in QtWidgets.QApplication.topLevelWidgets():    
        if widget.objectName() == name:
            return widget
    return None

def windowCheck(object,parent):
    for child in parent.children():
        if child.objectName() == object:
            child.deleteLater()

class ListView(QtWidgets.QWidget):
    def __init__(self,layoutDir = "H",*args,**kwargs):
        super(ListView,self).__init__(*args,**kwargs)

        if layoutDir == "H":
            self.layout = QtWidgets.QHBoxLayout(self)
        
        elif layoutDir == "V":
            self.layout = QtWidgets.QVBoxLayout(self)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.view = QtWidgets.QListView()
        self.model = QStandardItemModel()
        self.view.setModel(self.model)

        self.layout.addWidget(self.view)

    def setData(self,data):
        self.view.selectionModel().blockSignals(True)
        self.model.clear()        
        for i in range(0,len(data)):
            self.model.setItem(i, 0, QtGui.QStandardItem(data[i]))

        self.view.selectionModel().blockSignals(False)

    def setSelectItem(self,items):
        self.view.selectionModel().blockSignals(True)
        self.view.selectionModel().clearSelection()

        selected = False

        for i in range(0,self.model.rowCount()):     
            if self.model.index(i,0).data() in items:
                self.view.selectionModel().select(self.model.index(i,0),QtCore.QItemSelectionModel.Select)
                self.view.selectionModel().setCurrentIndex(self.model.index(i,0),QtCore.QItemSelectionModel.Select)
                selected = True
                break

        self.view.selectionModel().blockSignals(False)
        return selected

    def clearSelection(self):
        self.view.selectionModel().blockSignals(True)
        self.view.selectionModel().clearSelection()
        self.view.selectionModel().blockSignals(False)

    def selectedItem(self):
        modelIndex = self.view.selectionModel().selectedIndexes()
        
        items = []
        for index in modelIndex:
            items.append(self.model.data(index))

        return items

    def allData(self):
        items = []

        for i in range(0,self.model.rowCount()):
            items.append(self.model.index(i,0).data())

        return items

class QStandardItemModel(QtGui.QStandardItemModel):
    def __init__(self,*args,**kwargs):
        super(QStandardItemModel,self).__init__(*args,**kwargs)
        self.conditions = None
        self.cndColors = {
                            False :QtGui.QColor("#ed4407"),
                            True:QtGui.QColor("#ffffff")                                 
                        }

    def setCondition(self,conditions):        
        self.conditions = conditions
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def data(self, index, role=QtGui.Qt.DisplayRole,*args,**kwargs):
        
        if self.conditions != None and role == QtGui.Qt.TextColorRole:            
            text = index.data(QtGui.Qt.DisplayRole)
            
            for key in list(self.conditions.keys()):
                if text in self.conditions[key]:
                    return self.cndColors[key]
        
        try:
            return super(QStandardItemModel, self).data(index, role)
        except:
            return None

class FilePathField(QtWidgets.QWidget):
    itemChanged = QtCore.Signal(str)

    def __init__(self,mode = "directory",createBtns = ["set","clear"],filter = "Any files (*)",*args,**kwargs):
        super(FilePathField,self).__init__(*args,**kwargs)

        self.mode = mode
        self.filter = filter
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.field = QtWidgets.QLineEdit()
        self.layout.addWidget(self.field)

        if "set" in createBtns:
            self.setBtn = QtWidgets.QPushButton("set")
            self.layout.addWidget(self.setBtn)
            self.setBtn.clicked.connect(self.selectItem)
            self.setBtn.setMinimumWidth(40)
            self.setBtn.setMaximumWidth(40)

        if "open" in createBtns:
            self.openBtn = QtWidgets.QPushButton("open")
            self.layout.addWidget(self.openBtn)    
            self.openBtn.clicked.connect(self.openDirctory)
            self.openBtn.setMinimumWidth(40)
            self.openBtn.setMaximumWidth(40)

        if "clear" in createBtns:
            self.clearBtn = QtWidgets.QPushButton("clear")
            self.layout.addWidget(self.clearBtn)    
            self.clearBtn.clicked.connect(self.clearItem)
            self.clearBtn.setMinimumWidth(40)
            self.clearBtn.setMaximumWidth(40)

    def selectItem(self):
        curPath = self.field.text()
        
        if os.path.isdir(curPath) ==False:
            curPath = os.path.dirname(curPath)

        if self.mode == "directory":
            fileDialog = QtWidgets.QFileDialog.getExistingDirectory(self, "select Directory",curPath)
            
            if fileDialog == "":
                return
            
            targetPath = fileDialog.replace(os.path.sep, '/')
            if targetPath.endswith("/") ==False:
                targetPath = targetPath+ "/"
                
            self.field.setText(targetPath)
            self.itemChanged.emit(targetPath)


        elif self.mode == "file":

            if self.filter == None:
                fileDialog,accept = QtWidgets.QFileDialog.getOpenFileName(self, "select file",curPath)
            else:
                fileDialog,accept = QtWidgets.QFileDialog.getOpenFileName(self, "select file",curPath,self.filter)
            
            if accept == False or fileDialog == "":
                return
            
            targetPath = fileDialog.replace(os.path.sep, '/')
            self.field.setText(targetPath)
            self.itemChanged.emit(targetPath)

    def setItem(self,object,block = False):

        if block:
            self.field.blockSignals(True)
            self.blockSignals(True)

        self.field.setText(object)

        if block:
            self.field.blockSignals(False)
            self.blockSignals(False)

    def clearItem(self):
        self.field.setText("")

    def openDirctory(self):
        path = self.field.text()
        path = path.replace("/",os.path.sep)
        if os.path.isdir(path):   
            if mayaVer in ["2020","2019"]:
                path = b'explorer ' + path.encode("mbcs")
            else:
                path = 'explorer ' + path
            subprocess.Popen(path,shell =True)

    def read(self):
        return self.field.text()


class RadioButton(QtWidgets.QWidget):
    def __init__(self,options,btnType,btnSize = [60,20],*args,**kwargs):
        super(RadioButton,self).__init__(*args,**kwargs)

        self.options = options
        self.buttons = {}
        self.type = btnType
        self.btnSize = btnSize

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.radioGP = QtWidgets.QButtonGroup()
        self.setItems()
        self.radioGP.setExclusive(True)
    
    def setEnabled(self,enable):
        for button in self.buttons.values():
            button.setEnabled(enable)

    def clearItems(self):
        for button in self.buttons.values():
            self.radioGP.removeButton(button)
            button.hide()

        self.buttons = {}

    def setItems(self):
        self.clearItems()

        for i in range(0,len(self.options)):
            option = self.options[i]
            if self.type == "radio":
                widget = QtWidgets.QRadioButton(option)                
                
            elif self.type == "push":
                widget = QtWidgets.QPushButton(option)            
                widget.setFixedSize(self.btnSize[0],self.btnSize[1])                
                widget.setCheckable(True)
            
            self.layout.addWidget(widget)
            self.radioGP.addButton(widget,i)
            self.buttons[option] = widget

    def readSelectedText(self):
        return self.options[self.radioGP.checkedId()]
    
    def setSelectText(self,value):
        for i in range(0,len(self.options)):
            if value == self.options[i]:
                button = self.radioGP.button(i)
                button.setChecked(True)


class ComboBox(QtWidgets.QWidget):
    def __init__(self,data,*args,**kwargs):
        super(ComboBox,self).__init__(*args,**kwargs)

        self.data = data
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.box = QtWidgets.QComboBox()
        self.layout.addWidget(self.box)

        for item in self.data:
            self.box.addItem(item)    

        self.box.update()

    def setData(self,data):
        self.clearItems()

        self.box.blockSignals(True)
        self.data = data
        for item in self.data:
            self.box.addItem(item)

        self.box.update()
        self.box.blockSignals(False)
    
    def clearItems(self):

        self.box.blockSignals(True)
        self.box.clear()
        self.box.update()
        self.box.blockSignals(False)

    def readText(self):
        return self.box.currentText()			
        
    def readIndex(self):
        return self.box.currentIndex()
        
    def selectText(self,text,block=False):
        
        if block:
            self.box.blockSignals(True)
        
        if text in self.data:
            self.box.setCurrentIndex(self.data.index(text))
    
        if block:
            self.box.blockSignals(False)

    def selectIndex(self,index):
        self.box.setCurrentIndex(index)


class GetTimeRangeDialog(QtWidgets.QDialog):
    def __init__(self,*args, **kwargs):
        super(GetTimeRangeDialog,self).__init__(*args,**kwargs)

        self.start = None
        self.end = None
        mainLayout = QtWidgets.QVBoxLayout(self)

        self.rangeOpt = RadioButton(["animation","timeSlider","renderSetting","selection"],"push",[80,20])
        self.rangeOpt.radioGP.buttonClicked.connect(self.getValue)
        mainLayout.addWidget(self.rangeOpt)

        rangeLayout = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(rangeLayout)
        self.startFld = QtWidgets.QLineEdit()
        self.endFld = QtWidgets.QLineEdit()
        self.startFld.setEnabled(False)
        self.endFld.setEnabled(False)
        
        rangeLayout.addWidget(self.startFld)
        rangeLayout.addWidget(self.endFld)

        btnLayout = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(btnLayout)

        acceptBtn = QtWidgets.QPushButton("set")
        cancelBtn = QtWidgets.QPushButton("cancel")
        acceptBtn.clicked.connect(self.apply)
        cancelBtn.clicked.connect(self.reject)
        btnLayout.addWidget(acceptBtn)
        btnLayout.addWidget(cancelBtn)

    def getValue(self):
        self.start,self.end = getFrameRange(self.rangeOpt.readSelectedText())
        self.startFld.setText(str(self.start))
        self.endFld.setText(str(self.end))

    def apply(self):

        if self.start == None or self.end == None:
            self.reject()
        

        self.accept()

class PlayblastSettingWidget(QtWidgets.QGroupBox):
    def __init__(self,parentWidget,*args, **kwargs):
        super(PlayblastSettingWidget,self).__init__(*args,**kwargs)
        self.parentWidget = parentWidget
        outputSetLayout = QtWidgets.QFormLayout(self)

        ##output formatOption---------
        ##outputDir
        self.outputOpt = RadioButton(["project","custom"],"push",[60,20])
        self.outputOpt.setSelectText("project")
        self.outputOpt.radioGP.buttonClicked.connect(self.changeOutputOpt)

        outputSetLayout.addRow(QtWidgets.QLabel("outputDirectory:"),self.outputOpt)
        self.outputDirFld = FilePathField( mode = "directory",createBtns = ["set","open"])
        self.outputDirFld.field.editingFinished.connect(self.parentWidget.saveOutputOption)
        outputSetLayout.addRow(QtWidgets.QLabel(""),self.outputDirFld)

        ##file format (png)
        self.outputfileTypeOpt = ComboBox(["png","jpg","avi"])
        self.outputfileTypeOpt.box.currentIndexChanged.connect(self.parentWidget.saveOutputOption)
        outputSetLayout.addRow(QtWidgets.QLabel("fileFormat:"),self.outputfileTypeOpt)

        ## frameNumberOffset
        self.frameNumberOffsetOpt = QtWidgets.QCheckBox("")
        self.frameNumberOffsetOpt.stateChanged.connect(self.parentWidget.saveOutputOption)
        outputSetLayout.addRow(QtWidgets.QLabel("frameNumberOffset:"),self.frameNumberOffsetOpt)

        self.filenameFld = QtWidgets.QLineEdit("{scene}/{camera}/{scene}_{camera}")
        self.filenameFld.editingFinished.connect(self.parentWidget.saveOutputOption)
        outputSetLayout.addRow(QtWidgets.QLabel("filename:"),self.filenameFld)
        self.outputDirFld.setEnabled(False)

        applyPlayblastBtn = QtWidgets.QPushButton("apply playBlast All")
        applyPlayblastBtn.clicked.connect(ApplyFunc(self.parentWidget.applyPlayblastAll))
        outputSetLayout.addWidget(applyPlayblastBtn)

    def changeOutputOpt(self):
        curOpt = self.outputOpt.readSelectedText()
        if curOpt == "project":
            self.outputDirFld.setEnabled(False)
        elif curOpt == "custom":
            self.outputDirFld.setEnabled(True)
        
        self.parentWidget.saveOutputOption()

class CameraWidget(QtWidgets.QGroupBox):
    def __init__(self,parentWidget,*args, **kwargs):
        super(CameraWidget,self).__init__(*args,**kwargs)
        self.parentWidget = parentWidget

        mainLayout = QtWidgets.QHBoxLayout(self)

        cameraListLayout = QtWidgets.QVBoxLayout()
        mainLayout.addLayout(cameraListLayout)

        ##command
        camBtnLayout = QtWidgets.QHBoxLayout()
        cameraListLayout.addLayout(camBtnLayout)

        reloadCamBtn = QtWidgets.QPushButton("reload")
        camBtnLayout.addWidget(reloadCamBtn)
        reloadCamBtn.clicked.connect(self.reloadCameraList)

        self.orthographicChk = QtWidgets.QCheckBox("ignor orthographic")
        camBtnLayout.addWidget(self.orthographicChk)
        self.orthographicChk.setChecked(True)
        self.orthographicChk.stateChanged.connect(self.reloadCameraList)

        camBtnLayout.addStretch()

        ##list View----
        camViewLayout = QtWidgets.QHBoxLayout()
        cameraListLayout.addLayout(camViewLayout)

        self.cameraList = ListView()
        self.cameraList.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.cameraList.view.selectionModel().selectionChanged.connect(ApplyFunc(self.changeCamera)) 
        camViewLayout.addWidget(self.cameraList)

        ##camera info-----
        cameraInfoLayout = QtWidgets.QFormLayout()
        mainLayout.addLayout(cameraInfoLayout)
        
        ##playblast enable
        self.playblastEnBtn = QtWidgets.QPushButton("enable")
        self.playblastEnBtn.setCheckable(True)
        self.playblastEnBtn.clicked.connect(ApplyFunc(self.setCameraInfo,"playblast"))
        cameraInfoLayout.addRow(QtWidgets.QLabel("playblast:"),self.playblastEnBtn)

        ##range
        rangeLayout = QtWidgets.QHBoxLayout()
        self.startRangeFld = QtWidgets.QLineEdit()
        self.endRangeFld = QtWidgets.QLineEdit()
        self.startRangeFld.setEnabled(False)
        self.endRangeFld.setEnabled(False)
        
        self.rangeSetBtn = QtWidgets.QPushButton("set")
        
        rangeLayout.addWidget(self.startRangeFld)
        rangeLayout.addWidget(self.endRangeFld)
        rangeLayout.addWidget(self.rangeSetBtn)
        
        cameraInfoLayout.addRow(QtWidgets.QLabel("timeRange:"),rangeLayout)
        self.rangeSetBtn.clicked.connect(ApplyFunc(self.pickTimeRange))

        ##command

        cameraCmdLayout = QtWidgets.QHBoxLayout()
        cameraInfoLayout.addRow(cameraCmdLayout)

        playblastBtn = QtWidgets.QPushButton("playblast")
        playblastBtn.clicked.connect(ApplyFunc(self.parentWidget.applyPlayblast))
        cameraCmdLayout.addWidget(playblastBtn)

        openBtn = QtWidgets.QPushButton("openDir")
        openBtn.clicked.connect(ApplyFunc(self.parentWidget.openOutputDir))
        cameraCmdLayout.addWidget(openBtn)

        self.reloadCameraList()

    ##--------------------------------------------------------
    def pickTimeRange(self):
        if self.parentWidget.curCamera == "":
            return
        
        dialog = GetTimeRangeDialog(self.parentWidget)
        
        if dialog.exec_():
            self.parentWidget.curCameraInfo["startFrame"] = int(dialog.start)
            self.parentWidget.curCameraInfo["endFrame"] = int(dialog.end)

            self.setCameraInfo("timeRange")

        self.readCameraInfo()

    def readCameraInfo(self):
        self.parentWidget.curCameraInfo = getCameraInfo("cameraInfoSets",self.parentWidget.curCamera)

        ## enable playblast
        self.playblastEnBtn.blockSignals(True)
        self.playblastEnBtn.setChecked(self.parentWidget.curCameraInfo["playblast"])
        self.playblastEnBtn.blockSignals(False)

        ## range        
        self.startRangeFld.setText(str(self.parentWidget.curCameraInfo["startFrame"]))
        self.endRangeFld.setText(str(self.parentWidget.curCameraInfo["endFrame"]))

    def setCameraInfo(self,key):
        if key == "playblast":
            self.parentWidget.curCameraInfo["playblast"] = self.playblastEnBtn.isChecked()
            setCameraInfo(self.parentWidget.curCamera + "_infoSet",{"playblast":self.parentWidget.curCameraInfo["playblast"]})

        elif key == "timeRange":
            setCameraInfo(
                        self.parentWidget.curCamera + "_infoSet",
                        {
                            "startFrame": float(self.parentWidget.curCameraInfo["startFrame"]),
                            "endFrame":float(self.parentWidget.curCameraInfo["endFrame"]),
                            }
                        
                        )
            
    def changeCamera(self):
        self.parentWidget.curCamera = ""
        selects = self.cameraList.selectedItem()

        if len(selects) == 0:
            self.playblastEnBtn.setEnabled(False)
            self.rangeSetBtn.setEnabled(False)
            return
        
        self.playblastEnBtn.setEnabled(True)
        self.rangeSetBtn.setEnabled(True)

        self.parentWidget.curCamera = selects[-1]
        self.readCameraInfo()

        changeView(self.parentWidget.curCamera,None)
        start = cmds.playbackOptions(minTime=float(self.parentWidget.curCameraInfo["startFrame"]))
        end = cmds.playbackOptions(maxTime=float(self.parentWidget.curCameraInfo["endFrame"]))

    def reloadCameraList(self):
        self.playblastEnBtn.setEnabled(False)
        self.rangeSetBtn.setEnabled(False)
    
        nodes = listTypeNodes("camera")
        self.cameras = []
        
        for node in nodes:
            if self.orthographicChk.isChecked() == False:
                self.cameras.append(node)

            elif cmds.getAttr(node + ".orthographic") == False:
                self.cameras.append(node)

        self.cameras.sort()
        self.cameraList.setData(self.cameras)

class MainGUI(QtWidgets.QMainWindow):
    def __init__(self,parent,objectName,*args, **kwargs):
        super(MainGUI,self).__init__(parent=parent)
        
        self.setObjectName(objectName)
        self.setWindowTitle(objectName)

        self.curCamera = ""
        self.curCameraInfo = {}
        self.PBSettingActDict = {}
        self.PBHUDSettingActDict = {}
        self.optionDict = {}

        self.VIEWITEMSETTING = {
                        "cameras":          False,
                        "grid":             False,
                        "handles":          False,
                        "hairSystems":      False,
                        "headsUpDisplay":   True,
                        "ikHandles":        False,
                        "jointXray":        False,    
                        "manipulators":     False,
                        "motionTrails":     False,
                        "nCloths":          False,
                        "pivots":           False,
                        "activeComponentsXray": False,
                        "activeOnly":           False,
                        "dimensions":           False,
                        "displayAppearance":    "smoothShaded",
                        "displayTextures":      True,
                        "locators":             False,
                        "imagePlane":           False,
                        "joints":               False,
                        "nParticles":           True,
                        "polymeshes":           True,
                        "nurbsCurves":          False,
                        "nurbsSurfaces":        True,
                        "lights":               False,
                        "controlVertices":      False,
                        "selectionHiliteDisplay":   False
        }

        self.VIEWITEMSETTING_KEY = [
                                    "grid",
                                    "handles",
                                    "headsUpDisplay",
                                    "ikHandles",
                                    "manipulators",
                                    "motionTrails",
                                    "nCloths",
                                    "pivots",
                                    "activeOnly",
                                    "dimensions",
                                    "displayTextures",
                                    "locators",
                                    "imagePlane",
                                    "joints",
                                    "nParticles",
                                    "polymeshes",
                                    "nurbsCurves",
                                    "nurbsSurfaces",
                                    "lights",
                                    "controlVertices",
                                    "selectionHiliteDisplay"
                ]

        self.HUDSETTING = {
                        "resolutionGate":   False,
                        "cameranames":      True,
                        "focalLength":      True,
                        "sceneTimecode":    False,
                        "frameRate":        False,
                        "viewAxis":         True,
                        "currentFrame":     True
            }

        self.setupMenubar()
        self.setupWidgets()
        self.loadPBOption()
        self.loadOutputOption()

    def setupMenubar(self):
        ##setup menuBar
        self.menuBar = QtWidgets.QMenuBar(self)
        self.setMenuBar(self.menuBar)

        playbastSetting = QtWidgets.QMenu('playblastItems', self.menuBar)
        self.menuBar.addMenu(playbastSetting)

        playbastMenu = QtWidgets.QMenu('showItems', self.menuBar)
        playbastSetting.addMenu(playbastMenu)

        playbastHUDMenu = QtWidgets.QMenu('HUDItems', self.menuBar)
        playbastSetting.addMenu(playbastHUDMenu)

        self.PBSettingActDict = {}
        self.PBHUDSettingActDict = {}

        for settingKey in self.VIEWITEMSETTING_KEY:
            PBSettingAct = qaction(settingKey, playbastMenu)
            PBSettingAct.setCheckable(True)
            playbastMenu.addAction(PBSettingAct)
            PBSettingAct.triggered.connect(self.savePBOption)
            self.PBSettingActDict[settingKey] = PBSettingAct
        
        for settingKey in list(self.HUDSETTING.keys()):
            PBSettingAct = qaction(settingKey, playbastHUDMenu)
            PBSettingAct.setCheckable(True)
            playbastHUDMenu.addAction(PBSettingAct)
            PBSettingAct.triggered.connect(self.savePBOption)
            self.PBHUDSettingActDict[settingKey] = PBSettingAct

    def setupWidgets(self):
        self.mainWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.mainWidget)

        mainLayout = QtWidgets.QVBoxLayout(self.mainWidget)
       
        camWidget = CameraWidget(parentWidget=self)
        camWidget.setTitle("cameras")
        mainLayout.addWidget(camWidget)

        self.outputWidget = PlayblastSettingWidget(parentWidget=self)
        self.outputWidget.setTitle("output")
        mainLayout.addWidget(self.outputWidget)

    ##------------------------------------------------------------------------      
    def getPBSettings(self):
        self.PBSettingDict = {}
        self.HUDSettingDict = {}

        for settingKey in list(self.PBSettingActDict.keys()):
            PBSettingAct = self.PBSettingActDict[settingKey]
            self.PBSettingDict[settingKey] = PBSettingAct.isChecked()

        for settingKey in list(self.PBHUDSettingActDict.keys()):
            HUDSettingAct = self.PBHUDSettingActDict[settingKey]
            self.HUDSettingDict[settingKey] = HUDSettingAct.isChecked()

    def savePBOption(self):
        self.getPBSettings()
        saveDictOptionVar(self.objectName() + "_playblastItem",self.PBSettingDict)
        saveDictOptionVar(self.objectName() + "_playblastHUD",self.HUDSettingDict)

    def loadPBOption(self):
        self.PBSettingDict = dict(self.VIEWITEMSETTING)
        loadDict = {}
        loadDict = readDictOptionVar(self.objectName() + "_playblastItem")
        self.PBSettingDict.update(**loadDict)
        self.PBSettingDict["displayAppearance"] = "smoothShaded"

        for settingKey in list(self.PBSettingDict.keys()):
        
            if self.PBSettingDict[settingKey] == "True":
                self.PBSettingDict[settingKey] = True

            elif self.PBSettingDict[settingKey] == "False":
                self.PBSettingDict[settingKey] = False

            if settingKey in self.VIEWITEMSETTING_KEY:            
                PBSettingAct = self.PBSettingActDict[settingKey]    
                PBSettingAct.blockSignals(True)
            
                if self.PBSettingDict[settingKey] == True:                    
                    PBSettingAct.setChecked(True)
                            
                PBSettingAct.blockSignals(False)
        
        self.HUDSettingDict = dict(self.HUDSETTING)
        loadDict = {}
        loadDict = readDictOptionVar(self.objectName() + "_playblastHUD")
        self.HUDSettingDict.update(**loadDict)
        
        for settingKey in list(self.PBHUDSettingActDict.keys()):
            PBSettingAct = self.PBHUDSettingActDict[settingKey]
            
            PBSettingAct.blockSignals(True)

            if self.HUDSettingDict[settingKey] == "True" or self.HUDSettingDict[settingKey] == True:
                self.HUDSettingDict[settingKey] = True
                PBSettingAct.setChecked(True)
            else:
                self.HUDSettingDict[settingKey] = False

            PBSettingAct.blockSignals(False)

    ##------------------------------------------------------------------------      
    def saveOutputOption(self):
        self.optionDict = {
                        "outputOpt":        self.outputWidget.outputOpt.readSelectedText(),
                        "outputFormat":     self.outputWidget.outputfileTypeOpt.readText(),
                        "outputDir":        self.outputWidget.outputDirFld.read(),
                        "fileNameFormat":   self.outputWidget.filenameFld.text(),
                        "frameNumberOffset":   self.outputWidget.frameNumberOffsetOpt.isChecked()
                    }
        
        saveDictOptionVar(self.objectName() + "_playblastOutput",self.optionDict)

    def loadOutputOption(self):

        self.optionDict = {
                        "outputOpt":"project",
                        "outputDir":"",
                        "fileNameFormat":"{scene}/{camera}/{scene}_{camera}",
                        "outputFormat":"png",
                        "frameNumberOffset":False
        }

        loadOptionDict = readDictOptionVar(self.objectName() + "_playblastOutput")
        self.optionDict.update(**loadOptionDict)
        
        self.outputWidget.outputOpt.setSelectText(self.optionDict["outputOpt"])

        self.outputWidget.outputDirFld.blockSignals(True)
        self.outputWidget.filenameFld.blockSignals(True)
        self.outputWidget.outputfileTypeOpt.blockSignals(True)
        self.outputWidget.frameNumberOffsetOpt.blockSignals(True)

        self.outputWidget.outputDirFld.setItem(self.optionDict["outputDir"])
        self.outputWidget.filenameFld.setText(self.optionDict["fileNameFormat"])
        self.outputWidget.outputfileTypeOpt.selectText(self.optionDict["outputFormat"])        
        self.outputWidget.frameNumberOffsetOpt.setChecked(eval("bool("+str(self.optionDict["frameNumberOffset"])+")"))
    
        self.outputWidget.outputDirFld.blockSignals(False)
        self.outputWidget.filenameFld.blockSignals(False)
        self.outputWidget.outputfileTypeOpt.blockSignals(False)
        self.outputWidget.frameNumberOffsetOpt.blockSignals(False)

    def openOutputDir(self):
        self.saveOutputOption()
        self.savePBOption()

        outputDir = ""
        if self.optionDict["outputOpt"] == "project":
            outputDir = cmds.workspace(q=True,rootDirectory = True) + cmds.workspace(fileRuleEntry = "images") + "/"
        elif self.optionDict["outputOpt"] == "custom":
            outputDir = self.optionDict["outputDir"]

        if self.curCamera == "":
            return
                        
        cameraInfo = getCameraInfo("cameraInfoSets",self.curCamera)
        timeRange = [cameraInfo["startFrame"],cameraInfo["endFrame"]]
        resolution = [cmds.getAttr("defaultResolution.width"),cmds.getAttr("defaultResolution.height")]
        outputFilePath = outputDir + generateOutputName(self.curCamera,self.optionDict["fileNameFormat"])
        
        outputDirPath = os.path.dirname(outputFilePath)
        path = outputDirPath.replace("/",os.path.sep)
    
        if os.path.isdir(path):                       
            path = 'explorer ' + path
            subprocess.Popen(path,shell =True)

    def applyPlayblast(self):
        self.saveOutputOption()
        self.savePBOption()

        outputDir = ""
        if self.optionDict["outputOpt"] == "project":
            outputDir = cmds.workspace(q=True,rootDirectory = True) + cmds.workspace(fileRuleEntry = "images") + "/"
        elif self.optionDict["outputOpt"] == "custom":
            outputDir = self.optionDict["outputDir"]

        checkNeedSave()

        if self.curCamera == "":
            return
                        
        cameraInfo = getCameraInfo("cameraInfoSets",self.curCamera)
        timeRange = [cameraInfo["startFrame"],cameraInfo["endFrame"]]
        resolution = [cmds.getAttr("defaultResolution.width"),cmds.getAttr("defaultResolution.height")]
        outputFilePath = outputDir + generateOutputName(self.curCamera,self.optionDict["fileNameFormat"])
        playBlastProcess(self.curCamera,self.PBSettingDict,self.HUDSettingDict,outputFilePath,self.optionDict["outputFormat"],timeRange,resolution,self.optionDict["frameNumberOffset"])

    def applyPlayblastAll(self):
        self.saveOutputOption()
        self.savePBOption()

        outputDir = ""
        if self.optionDict["outputOpt"] == "project":
            outputDir = cmds.workspace(q=True,rootDirectory = True) + cmds.workspace(fileRuleEntry = "images") + "/"
        elif self.optionDict["outputOpt"] == "custom":
            outputDir = self.optionDict["outputDir"]

        checkNeedSave()

        cameras = getPlayblastCam("cameraInfoSets")

        for camera in cameras:
            cameraInfo = getCameraInfo("cameraInfoSets",camera)
            timeRange = [cameraInfo["startFrame"],cameraInfo["endFrame"]]
            resolution = [cmds.getAttr("defaultResolution.width"),cmds.getAttr("defaultResolution.height")]
            outputFilePath = outputDir + generateOutputName(camera,self.optionDict["fileNameFormat"])
            playBlastProcess(camera,self.PBSettingDict,self.HUDSettingDict,outputFilePath,self.optionDict["outputFormat"],timeRange,resolution,self.optionDict["frameNumberOffset"])

##main----------------------------------------
def callCameraSwitcher():
    objectName = "SSCameraSwitcher"
    mayaMainWindow = getTopLevelWidget('MayaWindow')
    windowCheck(objectName,mayaMainWindow)
    mainGUI = MainGUI(parent = mayaMainWindow,objectName = objectName)

    mainGUI.show()
