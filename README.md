# SSCameraSwitcher


# インストールから起動

SSCameraSwitcher.py ファイルをpythonPathが通ってる場所に格納してください。
例) C:/Users/y9bos/Documents/maya/2025/scripts

mayaを起動後、下記のスクリプトで呼び出せます。

```python
import SSCameraSwitcher
SSCameraSwitcher.callCameraSwitcher()
```

# 機能

<img width="567" height="494" alt="image" src="https://github.com/user-attachments/assets/6954aa71-a825-4d65-a06e-b0a9f9caef77" />

- **cameras**
左上のリストにシーン内のカメラをリストします。  
ここで選択することで、アクティブになっているviewPortのカメラを切り替えます。  

カメラを選択すると、右側にカメラの情報が読み込まれます。  
**playblast** -> apply playBlast All でプレイブラストされるか否か  
**timeRange** -> このカメラの担当するフレームレンジ(set ボタンで設定ができます）  

これらの情報はシーン内に作られる cameraInfoSets 以下のobjectSetに格納されています。  
<img width="351" height="95" alt="image" src="https://github.com/user-attachments/assets/c5ce519f-ef1c-4fc8-8c47-e53f0a5012d7" />

- **output**
プレイブラストの出力設定を行います。  

**outputDirectory** -> 出力先フォルダを指定します。  

project = setProjectで指定されたimagesフォルダ  
custom = 下のフィールドで指定したフォルダ  

**fileFormat** -> 出力ファイル形式
とりあえず png / jpg / avi のみ対応

**frameNumberOffset** -> 連番出力時に連番を１から始めるか否か

**filename** -> 出力するファイル名のひな型
{scene}  は現在のシーン名に置きかわります。
{camera} はカメラ名に置き換わります

デフォルト状態での出力はこのようになります。
```
{scene}/{camera}/{scene}_{camera}.####.png
{scene}/{camera}/{scene}_{camera}.avi
```

**apply playBlast All** -> playblast = enable になっているカメラを全てプレイブラストします。


- **playblastItems**
メニューバーのplayblastItemsにて、プレイブラスト時のvirePortの固定設定を設定できます。







