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

  class loadMeeting extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      const callRestBusinessObjectsGetMeetingsResult = await Actions.callRest(context, {
        endpoint: 'businessObjects/get_Meetings',
        uriParams: {
          'Meetings_Id': $page.variables.meetingID,
        },
      });

      $page.variables.sentiment = callRestBusinessObjectsGetMeetingsResult.body.sentiment;
      $page.variables.summary = callRestBusinessObjectsGetMeetingsResult.body.summarization;
      $page.variables.transcriptionID = callRestBusinessObjectsGetMeetingsResult.body.transcriptionId;
      $page.variables.meetingName = callRestBusinessObjectsGetMeetingsResult.body.meetingName;
      return;
    }
  }

  return loadMeeting;
});
