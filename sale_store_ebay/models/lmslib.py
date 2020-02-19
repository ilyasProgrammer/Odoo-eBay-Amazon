# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This Python file uses the following encoding: utf-8
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.#
#
#    This module is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
the lmslib module contains classes that build the eBay LMS API call requests
and has the functionality to send them to the eBay server( sandbox and production ).
'''

__author__ = "Wesley Hansen"
__date__ = "12/19/2011 01:50:15 PM"



import httplib
import os, os.path
import sys
import gzip
import uuid
from lxml import etree
import base64

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO as StringIO

PRODUCTION = 'production'
SANDBOX = 'sandbox'


class LMSCall():
    '''
    This is the parent class of all LMS API calls that can be made to the eBay servers.
    This class will be able to connect to the server( sandbox or production), build
    a request, build appropriate headers, send the request, and get a response.
    '''
    
    _thisdir = os.path.abspath( os.path.dirname( __file__ ) )
    
    def __init__(self, environment, **kwargs):
        self._env = kwargs.get('environment', 'sandbox')
        self._credentials = {
            "developer_key"   : kwargs.get('developer_key', ''),
            "application_key" : kwargs.get('application_key', ''),
            "certificate_key" : kwargs.get('certificate_key', ''),
            "auth_token"      : kwargs.get('auth_token', ''),
        }
        self._headers = {}
        self._generate_headers()
        self._request = ""
        self._response = ""
        
        self._siteconfig = {
            'site_id'       : 100,
            'site_host'     : None,
            'site_location' : None,
        }
    
    def _generate_headers(self):
        '''
        Creates the base headers that every request needs
        '''
        self._headers['X-EBAY-SOA-SECURITY-TOKEN'] = self._credentials['auth_token']
        self._headers['Content-Type'] = 'text/xml'
        
    def sendRequest( self ):
        '''
        Connects to eBay server, and HTTPS POSTs the request with the given headers
        Returns the response xml or an error message where appropriate
        '''
        
        connection = httplib.HTTPSConnection( self._siteconfig['site_host'] )
        connection.request( "POST", self._siteconfig['site_location'], self._request, self._headers )
        
        response = connection.getresponse()
        
        if response.status != 200:
            raise Exception( "Error %s sending request: %s" % (response.status, response.reason ) )
        
        response_string = response.read()
        
        connection.close()
        self._response = response_string
        return response_string
        
    def _get_response( self ):
        '''
        Parses the response and determines if the call was successful or not
        
        Returns: True if response says "Success", False otherwise
        '''
        #Read the response into an etree
        tree = etree.fromstring( self._response )
        #If the ack tag has text that is 'Success', return True
        if tree.xpath( './/ns:ack', namespaces={'ns':'http://www.ebay.com/marketplace/services'} )[0].text == 'Success':
            return True
        return False
    
    def _get_failure( self ):
        '''
        Returns the Failure tuple that contains ('Failure', errorId, message )
        Should be standard for every LMSCall object
        
        Returns None if not a failure
        
        Note: must use _get_response() first to determine that response was a failure
        '''
        tree = etree.fromstring( self._response )
        #treelist = tree.xpath( './/ns:errorMessage', namespaces={'ns':'http://www.ebay.com/marketplace/services'} )
        namespace = '{http://www.ebay.com/marketplace/services}'
        error = {}
        
        for node in tree.getchildren():
            if node.text:
                error[node.tag.replace( namespace, '' )] = node.text
            
            if node.tag.endswith( 'errorMessage'):
                for child in node.getchildren():
                    if child.tag.endswith( 'error' ):
                        for thing in child.getchildren():
                            error[thing.tag.replace( namespace, '')] = thing.text
        return ('Failure', error )
        
        
        
    def _get_success( self, *args ):
        '''
        Returns the success tuple that contains( 'Success', *args )
        where *args is a list of tags whose text values need to be returned in 
        the success tuple
            args = ['fileReferenceId', 'jobId']
            ex: ('Success', 1223151523, 153151634213 )
            
        Note: Must use _get_response() first to determine that response was a success
        '''
        tree = etree.fromstring( self._response )
        values = []
        namespace = 'http://www.ebay.com/marketplace/services'
        response_dict = {}
        for child in tree.getchildren():
            response_dict[child.tag.replace( '{%s}'% namespace , '')] = child.text
            
        success = ('Success', response_dict )
        return success

    def getResponse( self ):
        '''
        Reads the response, and if call was a success, it returns a success tuple
        A success tuple contains the string 'Success' and is then followed
        by the arguments specific to the call given
        If call was a failure it returns a tuple containing
        ('Failure', ErrorId, Message )
        '''
        
        if self._get_response() == True:
            tree = etree.fromstring( self._response )
            return self._get_success( *self.args )
        else:
            return self._get_failure()  
    
class BulkDataExchangeService( LMSCall ):
    '''
    This class is a wrapper for the LMSCall class that contains information on which
    server to connect to in order to make calls in the BulkDataExchange API
    '''
    
    def __init__( self, environment, **kwargs ):
        LMSCall.__init__( self, environment, **kwargs )
        
        if environment == PRODUCTION:
            self._siteconfig['site_host'] = 'webservices.ebay.com'
            self._siteconfig['site_location']  = '/BulkDataExchangeService'
            
        elif environment == SANDBOX:
            self._siteconfig['site_host'] = 'webservices.sandbox.ebay.com'
            self._siteconfig['site_location'] = '/BulkDataExchangeService'
            
        self._headers['X-EBAY-SOA-SERVICE-NAME'] = 'BulkDataExchangeService'
            

class FileTransferService( LMSCall ):
    '''
    This class is a wrapper for the LMSCall class that contains information on which 
    server to connect to in order to make calls in the FileTransfer API
    '''
    
    def __init__( self, environment, **kwargs ):
        LMSCall.__init__(self, environment, **kwargs )
        
        if environment == PRODUCTION:
            self._siteconfig['site_host'] = 'storage.ebay.com'
            self._siteconfig['site_location'] = '/FileTransferService'
            
        elif environment == SANDBOX:
            self._siteconfig['site_host'] = 'storage.sandbox.ebay.com'
            self._siteconfig['site_location'] = '/FileTransferService'
        
        self._headers['X-EBAY-SOA-SERVICE-NAME'] = 'FileTransferService'

class CreateUploadJob( BulkDataExchangeService ):
    '''
    This class is a wrapper for the BulkDataService class that is used to build the
    request string for a createUploadJob LMS API call.  
    '''
    
    def __init__( self, environment, **kwargs ):
        BulkDataExchangeService.__init__( self, environment, **kwargs )
        self._headers['X-EBAY-SOA-OPERATION-NAME'] = 'createUploadJob'
        self.args = ['jobId', 'fileReferenceId']
    
    def buildRequest( self, jobType, fileType='gzip', uuid=None ):
        '''
        This function builds the request string for a CreateUploadJob with the
        given jobType and fileType.
        
        Args:
            jobType(string): The Trading API call that this job is created to process.
            fileType(string): The file type of the data that will be uploaded. gzip by default
            uuid(string): A uuid to be used to keep track of jobs( None by default (optional))
        '''
        
        request  = '<?xml version="1.0" encoding="UTF-8"?>\r\n'
        request += '<createUploadJobRequest xmlns="http://www.ebay.com/marketplace/services">\r\n'
        if uuid:
            request += '<UUID>%s</UUID>\r\n' % uuid
        request += '<uploadJobType>%s</uploadJobType>\r\n' % jobType
        request += '<fileType>%s</fileType>\r\n' % fileType
        request += '</createUploadJobRequest>'
        
        self._request = request
            
class UploadFile( FileTransferService ):
    '''
    This class is a wrapper for the FileTransferService class that will build the proper
    request string for an uploadFile LMS API call.
    '''
            
    MIME_BOUNDARY = "MIME_BOUNDARY_UPLOADFILE"
    URN_UUID_REQUEST = uuid.uuid4()
    URN_UUID_ATTACHMENT = uuid.uuid4()
            
    def __init__( self, environment, **kwargs ):
        FileTransferService.__init__( self, environment, **kwargs )
        
        self._headers['X-EBAY-SOA-OPERATION-NAME'] = 'uploadFile'
        #Set Multipart Content-Type string
        content_type_string  = 'multipart/related;'
        content_type_string += ' boundary=%s;' % self.MIME_BOUNDARY
        content_type_string += ' type="application/xop+xml";'
        content_type_string += ' start="%s";' % self.URN_UUID_REQUEST
        content_type_string += ' start-info="text/xml"'
        self._headers['Content-Type'] = content_type_string
        
        self.args = []
        
    def _buildxml( self, request_dict ):
        '''
        Build the xml request portion of the request
        
        Args:
            request_dict(dict): Contains job creation information, including: taskReferenceId, fileReferenceId, and fileFormat
        '''
        request  = '<uploadFileRequest xmlns:sct="http://www.ebay.com/soaframework/common/types" xmlns="http://www.ebay.com/marketplace/services">\r\n'
        request += '<taskReferenceId>%s</taskReferenceId>\r\n' % request_dict['taskReferenceId']
        request += '<fileReferenceId>%s</fileReferenceId>\r\n' % request_dict['fileReferenceId']
        request += '<fileFormat>%s</fileFormat>\r\n' % request_dict['fileFormat']
        request += '<fileAttachment>\r\n'
        request += '<Size>%s</Size>\r\n'% request_dict['Size']
        request += '<Data><xop:Include xmlns:xop="http://www.w3.org/2004/08/xop/include" href="cid:%s"/></Data>\r\n' % self.URN_UUID_ATTACHMENT
        request += '</fileAttachment>\r\n'
        request += '</uploadFileRequest>\r\n'

        return str(request)
    
    def _build_mime_message( self, request, data ):
        '''
        Build the xml string with MIME attachments and the binary data
        
        Args:
            request(string):The xml request string for uploadFile api call
            data(binarystring): The binary string representation of the data
            to be attached to the xml request
        '''

        request_part  = '\r\n'
        request_part += '--%s\r\n' % self.MIME_BOUNDARY
        request_part += 'Content-Type: application/xop+xml; charset=UTF-8; type="text/xml"\r\n'
        request_part += 'Content-Transfer_Encoding: binary\r\n'
        request_part += 'Content-ID: %s\r\n\r\n' % self.URN_UUID_REQUEST
        request_part += '%s\r\n' % request

        if isinstance(request_part, unicode):
            print '0-----------------Request part is a unicode'

        binary_part  = b'\r\n'
        binary_part += b'--%s\r\n' % self.MIME_BOUNDARY
        binary_part += b'Content-Type: application/octet-stream\r\n'
        binary_part += b'Content-Transfer-Encoding: binary\r\n'
        binary_part += b'Content-ID: <%s>\r\n\r\n' % self.URN_UUID_ATTACHMENT
        binary_part += '%s\r\n' % data
        binary_part += b'--%s--' % self.MIME_BOUNDARY
        binary_part += b'\r\n'

        return request_part + binary_part
        
    def _generate_data( self, filename ):
        '''
        Compress the supplied data with gzip, and return it
        
        Args:
            filename( string ): the filename(and path) of the flie that will be
            compressed
        '''

        mybuffer = StringIO.StringIO()
        fp = open( filename, 'rb' )
        #Create a gzip object that reads the compression to StringIO buffer
        gzipbuffer = gzip.GzipFile( 'uploadcompression.xml.gz', 'wb', 9, mybuffer )
        gzipbuffer.writelines( fp )
        gzipbuffer.close()
        fp.close()
        
        mybuffer.seek(0)
        data = mybuffer.read()
        mybuffer.close()
        
        return data
        
    def buildRequest( self, jobID, fileID, filename ):
        '''
        This function builds the request string for an uploadFile api call with the
        given jobID, fileID, and filename.
        
        Args:
            jobID(string): A taskReferenceId that was generated from a createUploadJob call
            fileID(string): A fileReferenceId that was generated from a createUploadJob call
            filename(string): The filename( path) of the data file to be uploaded 
        '''
    
        data = self._generate_data( filename )
        
        request_dict = {
            'Size'              : long( sys.getsizeof( data ) ),
            'fileFormat'        : 'gzip',
            'fileReferenceId'   : fileID,
            'taskReferenceId'   : jobID,
        }
        
        request = self._buildxml( request_dict )
        request = self._build_mime_message( request, data )
        self._request = request

        
class StartUploadJob( BulkDataExchangeService ):
    '''
    This class is a wrapper for the BulkDataExchangeService class that will build the proper
    request string for startUploadJob LMS API call.
    '''
    
    def __init__( self, environment, **kwargs):
        BulkDataExchangeService.__init__(self, environment, **kwargs)
        self._headers['X-EBAY-SOA-OPERATION-NAME'] = 'startUploadJob'
        self.args = []
        
    def buildRequest( self, jobID ):
        '''
        This function builds the request string for a startUploadJob api call with 
        the given jobID
        
        Args:
            jobID(string): A taskReferenceId that was generated from a createUploadJob call
        '''
        request  = '<?xml version="1.0" encoding="utf-8"?>\r\n'
        request += '<startUploadJobRequest xmlns="http://www.ebay.com/marketplace/services">\r\n'
        request += '<jobId>%s</jobId>\r\n' % jobID
        request += '</startUploadJobRequest>\r\n'
        
        self._request = request
        

class GetJobStatus( BulkDataExchangeService ):
    '''
    This class is a wrapper for the BulkdDataExchangeService class that will build the proper
    request string for getJobStatus LMS API call
    '''
    
    def __init__( self, environment, **kwargs ):
        BulkDataExchangeService.__init__(self, environment, **kwargs)
        self._headers['X-EBAY-SOA-OPERATION-NAME'] = 'getJobStatus'
        self.args = []
        
    def buildRequest( self, jobID ):
        '''
        This function builds the request string for a getJobStatus api call with
        the given jobID
        
        Args:
            jobID(string): A taskReferenceId that was generated from a createUploadJob call
        '''
        
        request  = '<?xml version="1.0" encoding="utf-8"?>\r\n'
        request += '<getJobStatusRequest xmlns="http://www.ebay.com/marketplace/services">\r\n'
        request += '<jobId>%s</jobId>\r\n' % jobID
        request += '</getJobStatusRequest>\r\n'
        
        self._request = request
        
    def _build_job_profile( self ):
        '''
        Parses the response and inserts the data in the jobProfile tree into a
        dictionary that it returns
        '''
        tree = etree.fromstring( self._response )
        namespace = "http://www.ebay.com/marketplace/services"
        #Find all nodes of 'jobProfile'
        treelist = tree.xpath( ".//ns:jobProfile", namespaces={'ns':namespace} )
        
        profiles = []
        for node in treelist:
            profile = {}
            for child in node.getchildren():
                profile[child.tag.replace( '{%s}'% namespace , '')] = child.text
            profiles.append( profile)
                
        return profiles
            
        
    def getResponse( self ):
        '''
        Reads the response, and if call was a success, it returns a success tuple
        A success tuple contains the string 'Success' and is then followed
        by the arguments specific to the call given
        If call was a failure it returns a tuple containing
        ('Failure', ErrorId, Message )
        '''
        

        if self._get_response() == True:
            return ("Success", self._build_job_profile() )
        else:
            return self._get_failure()
            

class AbortJob( BulkDataExchangeService ):
    '''
    This class is a wrapper for the BulkdDataExchangeService class that will build the proper
    request string for abortJob LMS API call
    '''
    
    def __init__( self, environment, **kwargs ):
        BulkDataExchangeService.__init__(self, environment, **kwargs)
        self._headers['X-EBAY-SOA-OPERATION-NAME'] = 'abortJob'
        self.args = []
        
    def buildRequest( self, jobID ):
        '''
        This function builds the request string for a abortJob api call with
        the given jobID
        
        Args:
            jobID(string): A taskReferenceId that was generated from a createUploadJob call
        '''
        
        request  = '<?xml version="1.0" encoding="utf-8"?>\r\n'
        request += '<abortJobRequest xmlns="http://www.ebay.com/marketplace/services">\r\n'
        request += '<jobId>%s</jobId>\r\n' % jobID
        request += '</abortJobRequest>\r\n'
        
        self._request = request 
        
        
class GetJobs( BulkDataExchangeService ):
    '''
    This class is a wrapper for the BulkdDataExchangeService class that will build the proper
    request string for getJobs LMS API call
    '''
    
    def __init__( self, environment, **kwargs ):
        BulkDataExchangeService.__init__(self, environment, **kwargs)
        self._headers['X-EBAY-SOA-OPERATION-NAME'] = 'getJobs'
        self.args = []
        
    def buildRequest( self, **kwargs ):
        '''
        This function builds the request string for a getJobs api call      
        '''
        
        request  = '<?xml version="1.0" encoding="utf-8"?>\r\n'
        request += '<getJobsRequest xmlns="http://www.ebay.com/marketplace/services">\r\n'
        if kwargs.get('jobType'):
            request += '<jobType>%s</jobType>\r\n' %kwargs.get('jobType')
        if kwargs.get('jobStatus'):
            request += '<jobStatus>%s</jobStatus>\r\n' %kwargs.get('jobStatus')
        request += '</getJobsRequest>\r\n'
        
        self._request = request

    def _build_job_profile( self ):
        '''
        Parses the response and inserts the data in the jobProfile tree into a
        dictionary that it returns
        '''
        tree = etree.fromstring( self._response )
        namespace = "http://www.ebay.com/marketplace/services"
        #Find all nodes of 'jobProfile'
        treelist = tree.xpath( ".//ns:jobProfile", namespaces={'ns':namespace} )
        
        profiles = []
        for node in treelist:
            profile = {}
            for child in node.getchildren():
                profile[child.tag.replace( '{%s}'% namespace , '')] = child.text
            profiles.append( profile)
                
        return profiles
            
        
    def getResponse( self ):
        '''
        Reads the response, and if call was a success, it returns a success tuple
        A success tuple contains the string 'Success' and is then followed
        by the arguments specific to the call given
        If call was a failure it returns a tuple containing
        ('Failure', ErrorId, Message )
        '''
        

        if self._get_response() == True:
            return ("Success", self._build_job_profile() )
        else:
            return self._get_failure()
            
class DownloadFile( FileTransferService ):
    '''
    This class is a wrapper for the FileTransferService class that will build the proper
    request string for a DownloadFile LMS API call.
    '''
        
    def __init__( self, environment, **kwargs ):
        FileTransferService.__init__( self, environment, **kwargs )
    
        self._headers['X-EBAY-SOA-OPERATION-NAME'] = 'downloadFile'
        self._headers['Content-Type'] = 'text/xml'
        self.args = []
        
        #print self._headers
        
    def buildRequest( self, jobID, fileID ):
        '''
        This function builds the request string for an uploadFile api call with the
        given jobID, fileID, and filename.
        
        Args:
            jobID(string): A taskReferenceId that was generated from a createUploadJob call
            fileID(string): A new fileReferenceId that was generated from a getJobStatus call
        '''
        
        request  = '<?xml version="1.0" encoding="utf-8"?>\r\n'
        request = '<downloadFileRequest xmlns="http://www.ebay.com/marketplace/services">\r\n'
        request += '<taskReferenceId>%s</taskReferenceId>\r\n' % jobID
        request += '<fileReferenceId>%s</fileReferenceId>\r\n' % fileID
        request += '</downloadFileRequest>\r\n'

        self._request = request
    
    def getResponse( self ):
        '''
        Reads the response, and if call was a success, it returns a "Success" and the response
        in a tuple.  If it was a failure, it returns "Failure" and the respones in a tuple
        '''
        #Break up the response into xml and data chunks
        self._parse_response()

        return FileTransferService.getResponse(self)
        
    def _parse_response( self ):
        '''
        Parses the response string returned by the eBay server and separates the information
        into two parts: the xml response part and zipfile part
        '''
        #Find boundary string
        boundary = self._response.splitlines()[0]
        
        #Find the ending boundary index
        find = self._response.find( "Content-ID:" )
        find = self._response.find( '\r\n', find )
        
        #Find start of middle boundary
        middle_boundary = self._response.find( boundary, find )
        
        #XML response from downloadFile
        response = self._response[find:middle_boundary].strip()
        
        #Find next boundary
        find = self._response.find( "Content-ID:", middle_boundary )
        find = self._response.find( '\r\n', find )
        find_end = self._response.find( boundary, find )
        
        #Extract the compressed data and write it to file
        data = self._response[find:find_end]
        fp = open( '/var/tmp/data_responses.zip', 'wb' )
        fp.write( data )
        fp.close()
        
        self._response = response


class StartDownloadJob( BulkDataExchangeService ):
    '''
    This class contains information to construct a startDownloadJob request
    that allows us to generate reports about inventory, sales, etc 
    '''
    
    def __init__( self, environment, **kwargs ):
        BulkDataExchangeService.__init__(self, environment, **kwargs)
        self._headers['X-EBAY-SOA-OPERATION-NAME'] = 'startDownloadJob'
        self.args = []
        self.allowable_jobtypes = ('ActiveInventoryReport', 'FeeSettlementReport', 'SoldReport')
    
        
    def buildRequest( self, jobType, uuid, listingType=None ):
        '''
        This function builds the request string for a abortJob api call with
        the given jobType
        
        Args:
            jobType[string]: Tells which job type request the job will make:
            One of ('ActiveInventoryReport', 'FeeSettlementReport', 'SoldReport')
            uuid[string]: A Universal Unique ID that is required in the request
            listingType[string]
        '''
        if jobType in self.allowable_jobtypes:
            request  = '<?xml version="1.0" encoding="utf-8"?>\r\n'
            request += '<startDownloadJobRequest xmlns="http://www.ebay.com/marketplace/services">\r\n'
            request += '<downloadJobType>%s</downloadJobType>\r\n' % jobType
            if listingType in ['Auction', 'AuctionAndFixedPrice', 'FixedPrice']:
                request += '<downloadRequestFilter>\r\n'
                request += '<activeInventoryReportFilter>\r\n'
                request += '<includeListingType>%s</includeListingType>\r\n' % listingType
                request += '</activeInventoryReportFilter>\r\n'
                request += '</downloadRequestFilter>\r\n'
            request += '<UUID>%s</UUID>\r\n' % uuid
            request += '</startDownloadJobRequest>\r\n'

            self._request = request
            