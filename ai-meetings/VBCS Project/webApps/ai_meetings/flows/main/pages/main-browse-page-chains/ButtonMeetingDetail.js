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

  class ButtonMeetingDetail extends ActionChain {

    /**
     * @param {Object} context
     * @param {Object} params
     * @param {any} params.key 
     * @param {number} params.index 
     * @param {any} params.current 
     */
    async run(context, { key, index, current }) {
      const { $page, $flow, $application } = context;

/*
alert("key: "+key);
alert(current.row.transcriptionId);*/

 const navigateToPageMainStartResult = await Actions.navigateToPage(context, {
        page: 'main-start',
        params: {
          meetingID: key,
          transcriptionID: current.row.transcriptionId,
        },
      });

      // "Transcription ID: "+rowData.transcriptionId
    }
  }

  return ButtonMeetingDetail;
});
