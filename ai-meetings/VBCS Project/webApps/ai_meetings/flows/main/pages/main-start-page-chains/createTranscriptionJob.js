define([
  'vb/action/actionChain',
  'vb/action/actions',
  'vb/action/actionUtils',
], (
  ActionChain,
  Actions,
  ActionUtils
) => {
  'use strict';

  class createTranscriptionJob extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      const callRestCreateJobPostTranscriptionJobsResult = await Actions.callRest(context, {
        endpoint: 'CreateJob/postTranscriptionJobs',
        body: {
      "compartmentId":$application.variables.compartment_id,
      "displayName":"job-"+$page.variables.filename,
      "inputLocation": {
                    "locationType":"OBJECT_LIST_INLINE_INPUT_LOCATION", 
                    "objectLocations":
                                          [{
                                             "bucketName":$application.variables.bucketName, "namespaceName": $application.variables.namespace, "objectNames": [$page.variables.filename] 
                                          }]
                                      
                       },
      "modelDetails": 
         {
           "languageCode":"en",
            "modelType": "WHISPER_MEDIUM",
           "transcriptionSettings": {
                  "diarization": {
                    "isDiarizationEnabled": true, //"numberOfSpeakers": $page.variables.nParticipants
                    }
             }
         },
      "outputLocation": {
                          "bucketName":$application.variables.bucketName, "namespaceName":$application.variables.namespace, "prefix": "id"+$application.user.userId
                        }
      },
      });

      if (callRestCreateJobPostTranscriptionJobsResult.status===200 || callRestCreateJobPostTranscriptionJobsResult.status===201) {
        $page.variables.jobIdName = callRestCreateJobPostTranscriptionJobsResult.body.displayName;
        $page.variables.jobStatus = callRestCreateJobPostTranscriptionJobsResult.body.lifecycleState;
        $page.variables.jobId = callRestCreateJobPostTranscriptionJobsResult.body.id;

        const callRestBusinessObjectsCreateTranscriptionsResult = await Actions.callRest(context, {
          endpoint: 'businessObjects/create_Transcriptions',
          body: {
        "jobID": $page.variables.jobId,
        "jobNAME": $page.variables.jobIdName,
        "status": $page.variables.jobStatus
        },
        });

        const callRestBusinessObjectsUpdateMeetingsResult = await Actions.callRest(context, {
          endpoint: 'businessObjects/update_Meetings',
          uriParams: {
            'Meetings_Id': $page.variables.currentRequest,
          },
          body: {
         "transcriptionId": callRestBusinessObjectsCreateTranscriptionsResult.body.id
        },
        });

        await Actions.fireNotificationEvent(context, {
          summary: 'We are processing your request. It will take a while...',
          type: 'info',
          displayMode: 'transient',
        });

        return;
      } else {
        return;
      }
    }
  }

  return createTranscriptionJob;
});
