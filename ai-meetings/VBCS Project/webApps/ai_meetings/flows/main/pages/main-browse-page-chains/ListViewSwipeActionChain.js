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

  class ListViewSwipeActionChain extends ActionChain {

    /**
     * @param {Object} context
     * @param {Object} params
     * @param {string} params.navigationItem
     * @param {string} params.meetingsId
     * @param {any} params.rowData
     */
    async run(context, { navigationItem, meetingsId, rowData }) {
      const { $page, $flow, $application } = context;
      switch (navigationItem) {
        case 'delete':
                await Actions.fireNotificationEvent(context, {
                summary: 'Deleting meeting',
                type: 'confirmation',
                displayMode: 'transient',
              });

              const callRestBusinessObjectsDeleteMeetingsResult = await Actions.callRest(context, {
                endpoint: 'businessObjects/delete_Meetings',
                uriParams: {
                  'Meetings_Id': meetingsId,
                },
              });

              await Actions.fireDataProviderEvent(context, {
                refresh: null,
                target: $page.variables.meetingsListSDP,
              });
          break;
        case 'view':
          const navigateToPageMainStartResult = await Actions.navigateToPage(context, {
            page: 'main-start',
            params: {
              meetingID: meetingsId,
              transcriptionID: rowData.transcriptionId,
            },
          });
          break;
        default:
          break;
      }
    }
  }

  return ListViewSwipeActionChain;
});
