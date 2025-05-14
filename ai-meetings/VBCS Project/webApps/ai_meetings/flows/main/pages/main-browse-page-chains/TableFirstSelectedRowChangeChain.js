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

  class TableFirstSelectedRowChangeChain extends ActionChain {

    /**
     * @param {Object} context
     * @param {Object} params
     * @param {any} params.rowKey 
     * @param {any} params.rowData 
     */
    async run(context, { rowKey, rowData }) {
      const { $page, $flow, $application } = context;

     /* await Actions.fireNotificationEvent(context, {
        summary: "Meeting ID: "+rowKey,
        message: "Transcription ID: "+rowData.transcriptionId,
      });*/

      //alert(JSON.stringify(rowData));

     /* const navigateToPageMainStartResult = await Actions.navigateToPage(context, {
        page: 'main-start',
        params: {
          meetingID: rowKey,
          transcriptionID: rowData.transcriptionId,
        },
      });*/
    }
  }

  return TableFirstSelectedRowChangeChain;
});
