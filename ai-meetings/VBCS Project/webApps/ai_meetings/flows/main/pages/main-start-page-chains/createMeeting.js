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

  class createMeeting extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      if ($application.functions.isFormValid('oj-validation-group-upload')) {
        $page.variables.loading = true;
        let transcription = true;
        let summarization = true;
        let sentiment = true;
        let temp = "";//$page.variables.meetingParticipants.join(',');
        let internalM = true;
        let meetingDesc ="";
         $page.variables.requirements.push("transcription","summarization","sentiment_analysis");
             //    alert($page.variables.requirements[0]);
      


    
        const callRestBusinessObjectsCreateMeetingResult = await Actions.callRest(context, {
          endpoint: 'businessObjects/create_Meetings',
          body: {
         "internalMeeting":  internalM ,
         "meetingName":  $page.variables.meetingName ,
         "meetingDesc":  meetingDesc ,
         "speakersN":  $page.variables.nParticipants ,
         "speakersInvolved":  temp ,
         "transcription":  transcription ,
         "summarization": summarization,
         "sentiment":  sentiment ,
         "fname" : $page.variables.filename,
        },
        });

        if (callRestBusinessObjectsCreateMeetingResult.status===201) {

          $page.variables.currentRequest = callRestBusinessObjectsCreateMeetingResult.body.id;
          $page.variables.meetingID = callRestBusinessObjectsCreateMeetingResult.body.id;
          $page.variables.meetingCreated = true;

        $page.variables.transcriptionID =  $page.variables.meetingID;
          await Actions.callChain(context, {
            chain: 'createTranscriptionJob',
          });

          await Actions.fireNotificationEvent(context, {
            summary: 'Your meeting has been created successfully',
            displayMode: 'transient',
            type: 'confirmation',
          });
        } else {
          await Actions.fireNotificationEvent(context, {
            summary: 'There was a problem creating your meeting',
            type: 'warning',
            displayMode: 'transient',
          });
        }
      } else {
        await Actions.fireNotificationEvent(context, {
          summary: 'The Meeting name is mandatory',
          displayMode: 'transient',
          type: 'warning',
        });
      }

      $page.variables.loading = false;

      return;
    }
  }

  return createMeeting;
});
