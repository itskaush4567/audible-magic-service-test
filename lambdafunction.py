import subprocess
import os
import shutil
import boto3
import json
import gzip


def deleteAudioFile(fileName):
    response = '';
    try:
        subprocess.check_output('rm /tmp/' + fileName, stderr=subprocess.STDOUT, shell=True);
    except subprocess.CalledProcessError as e:
        raise Exception('Failed to delete file with name ' + fileName + ' in /tmp directory with error: ' + str(e));



def checkIfAudioFileContainsCopyrightContent(fileName):
    outputString = '';

    ## run executable
    try:
        outputString = subprocess.check_output('/tmp/identifyMediaFile -c /tmp/RobloxLR_v20.config -i /tmp/' + fileName +  ' -o /tmp/outputJsonFile', stderr=subprocess.STDOUT, shell=True);
    except subprocess.CalledProcessError as e:
        return 'Failed to run identifyMediaFile executable with error: ' + str(e);

    return outputString;


def getResponseContent():
    with open('/tmp/outputJsonFile', 'r') as content_file:
    	content = content_file.read()
    	return content

def parseFileNameFromS3Path(s3Path):
    startIndex = s3Path.rfind('/');
    fileName = s3Path[startIndex + 1:];
    return fileName;



def downloadFileFromS3(s3Path, fileName):
    s3 = boto3.resource('s3');
    try:
        ## Take out s3:// from string
        fullpath = s3Path[5:];
        lastIndexOfBucketName = fullpath.find('/');
        ## Get name of bucket from path
        bucketName = fullpath[:lastIndexOfBucketName];
        ## Get rest of path to audio file
        filePath = fullpath[lastIndexOfBucketName + 1:];
        
        ## Download file
        s3.meta.client.download_file(bucketName, filePath, '/tmp/' + fileName);
    except Exception as e:
        raise Exception('Failed to copy audio at s3 path ' + s3Path + ' to /tmp directory with error: ' + str(e));



def parseOutS3Path(event):
    try:
        s3Path = event['queryStringParameters']['s3Path'];
        return s3Path;
    except KeyError as e:
        raise Exception('Could not find key \'s3Path\' in the request body object');



def createLibCurlLink():
    try:
        subprocess.call('ln -s /usr/lib64/libcurl.so.4 libcurl.so', stderr=subprocess.STDOUT, shell=True);
    except subprocess.CalledProcessError as e:
        raise Exception('Failed to link to libcurl.so.4 library in /usr/lib64/ with error: ' + str(e));



def createAndReturnResponseObject(responseString, statusCode = 200):
    #headers = {};
    #headers['Access-Control-Allow-Origin'] = "*";
    output = {};
    #output['headers'] = headers;
    output['body'] = responseString;
    output['statusCode'] = statusCode;
    return output;



def lambda_handler(event, context):
    try:
        currentDirectory = os.getcwd();

        ## If the current directory is not /tmp do all set up work.
        if(currentDirectory != '/tmp'):
            ## move all files from deafult lambda current directory to /tmp.
            src = os.environ['LAMBDA_TASK_ROOT'] + '/';
            src_files = os.listdir(src);
            for file_name in src_files:
                full_file_name = os.path.join(src, file_name)
                if (os.path.isfile(full_file_name)):
                    shutil.copy(full_file_name, '/tmp');

            ## move into /tmp directory becuase Audible Magic writes to a file in the current
            ## working directory and in Lambda only files in /tmp can be written too.
            os.chdir('/tmp');



        # Create a link to the libcurl.so.4 library located in /usr/lib64.
        createLibCurlLink();

        ## Parse out s3 path from reuqest body, download file from s3 to /tmp directory,
        ## then parse out file name from s3 path.
        s3Path = parseOutS3Path(event);
        fileName = parseFileNameFromS3Path(s3Path);
        downloadFileFromS3(s3Path, fileName);
        
        #Rename file name
        newFileName = renameAndUnzipFile(fileName);
        
        # Find out if audio file contains copyright content or not.
        ## Return response 2006 = copyrighted, 2005 = not copyrighted, if not either
        ## then error message will be returned.
        audibleMagicResponseString = str.strip(checkIfAudioFileContainsCopyrightContent(newFileName));
        customResponse = getCustomResponse(audibleMagicResponseString);

        ## delete audio file from /tmp directory
        #deleteAudioFile(newFileName);
        #deleteAudioFile(fileName);

        ## Put response string into response body and return object with header and body.
        return createAndReturnResponseObject(customResponse);
    except Exception as e:
        error = {}
        error['response'] = str(e)
        return createAndReturnResponseObject(json.dumps(error), 500)

def renameAndUnzipFile(fileName):
    newFileName = fileName
    if fileName.find('.') == -1:
        newFileName = fileName + '.mp3'
        with gzip.open('/tmp/' + fileName, 'rb') as f_in:
            with open('/tmp/' + newFileName, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    return newFileName

def getCustomResponse(resCode):
    response = {}
    if resCode == "2005":
        response['response'] = "ok"
    elif resCode == "2006":
        response['response'] = "copyrighted"
        response['rawResponse'] = getResponseContent()
    elif resCode == "5429":
        response['response'] = "tooManyRequests"
        response['rawResponse'] = getResponseContent()
    elif resCode == "5503":
        response['response'] = "serviceUnavailable"
        response['rawResponse'] = getResponseContent()
    else:
        response['response'] = "unknown"
    return json.dumps(response)
	

#fileName = parseFileNameFromS3Path("s3://c4.roblox.com/3cfbc3e3317310cc16d05e87b6ada930");
#downloadFileFromS3("s3://c4.roblox.com/3cfbc3e3317310cc16d05e87b6ada930", fileName);
