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

  class ButtonMyMeetings extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      await Actions.resetVariables(context, {
        variables: [
          '$page.variables.transcriptionID',
          '$page.variables.jobId',
          '$page.variables.jobIdName',
          '$page.variables.currentRequest',
          '$page.variables.jobStatus',
          '$page.variables.parURL',
          '$page.variables.meetingID',
          '$page.variables.filename',
          '$page.variables.fileSize',
          '$page.variables.negative',
          '$page.variables.meetingCreated',
          '$page.variables.meetingName',
          '$page.variables.uploadSuccess',
          '$page.variables.jobCompletion',
        ],
      });
      
      const navigateToPageMainBrowseResult = await Actions.navigateToPage(context, {
        page: 'main-browse',
      });
    }
  }

  return ButtonMyMeetings;
});
