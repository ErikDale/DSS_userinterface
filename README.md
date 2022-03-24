# DSS_userinterface
This application is made mainly for Windows and the following steps are for Windows OS primarily.

## Run Application 
To run this program you can either use our .exe file or clone this repo and run our python file. 

### Use Our Executable File
Here: https://www.dropbox.com/s/2hiru2ho98sgeae/dss_userinterface.zip?dl=0 you can find a zip file containing our executable file. Simply download that, unzip it 
and run the dss_userinterface.exe file that is inside it. You unzip a zip-file by right clicking it and selecting "extract all": 

![](images/unzip.jpg "Unzip zip file")

If you move the .exe file from the folder it will not work, so keep it in the folder.

### Use Repository To Run Application
#### Install Python and Anaconda

To run our application using our repository you need to have python: https://www.python.org/downloads/ installed on your Windows computer.
I would also recommend you download Anaconda: https://www.anaconda.com/products/individual to make it easier to run the appliction.

#### Clone Repository
Clone repository in a wanted location on your computer using: 
```
$ git clone https://github.com/ErikDale/DSS_userinterface.git
```

#### Open Anaconda Prompt
Once you have installed Anaconda you should be able to press the Windows button and search for Anaconda Prompty: 

![](images/anaconda.jpg "Anaconda Prompt")

Once you have opened that you should navigate to the repo. You can do this by using: 
```
cd <full_path to the cloned the repo>
```
#### Use Pip Install
When you have navigated to the cloned the repo you should use: 
```
pip install -r requirements.txt
```
to install all the dependencies needed to run the application. 

#### Run Application
When that is done you should be able to run the application using: 
```
python ./dss_userinterface.py
```

 



