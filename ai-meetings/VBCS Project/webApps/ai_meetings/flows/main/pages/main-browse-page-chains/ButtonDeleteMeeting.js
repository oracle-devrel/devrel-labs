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

  class ButtonDeleteMeeting extends ActionChain {

    /**
     * @param {Object} context
     * @param {Object} params
     * @param {any} params.key 
     * @param {number} params.index 
     * @param {any} params.current 
     */
    async run(context, { key, index, current }) {
      const { $page, $flow, $application } = context;

      await Actions.fireNotificationEvent(context, {
        summary: 'Deleting meeting',
        type: 'confirmation',
        displayMode: 'transient',
      });

      const callRestBusinessObjectsDeleteMeetingsResult = await Actions.callRest(context, {
        endpoint: 'businessObjects/delete_Meetings',
        uriParams: {
          'Meetings_Id': key,
        },
      });

      await Actions.fireDataProviderEvent(context, {
        refresh: null,
        target: $page.variables.meetingsListSDP,
      });
    }
  }

  return ButtonDeleteMeeting;
});
