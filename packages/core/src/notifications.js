const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

const defaults = {
  STATE_DIR: path.join(process.env.HOME || require('os').homedir(), '.frugality/state'),
  NOTIFICATIONS_ENABLED: true
};

const notifications = {
  send: (title, message, options = {}) => {
    if (!defaults.NOTIFICATIONS_ENABLED && !options.force) {
      return { sent: false, reason: 'disabled' };
    }
    
    return new Promise((resolve) => {
      const platform = process.platform;
      
      let command;
      if (platform === 'darwin') {
        command = `osascript -e 'display notification "${message}" with title "${title}"'`;
      } else if (platform === 'linux') {
        command = `notify-send "${title}" "${message}"`;
      } else {
        resolve({ sent: false, reason: 'unsupported platform' });
        return;
      }
      
      exec(command, (error) => {
        if (error) {
          resolve({ sent: false, error: error.message });
        } else {
          resolve({ sent: true, title, message });
        }
      });
    });
  },

  notifyStart: (mode) => {
    return notifications.send(
      'Frugality Started',
      `Running in ${mode} mode`,
      { force: true }
    );
  },

  notifyStop: () => {
    return notifications.send(
      'Frugality Stopped',
      'System has been stopped',
      { force: true }
    );
  },

  notifyError: (error) => {
    return notifications.send(
      'Frugality Error',
      error,
      { force: true }
    );
  },

  notifyUpdate: (models) => {
    return notifications.send(
      'Models Updated',
      `Refreshed ${models} models`,
      { force: true }
    );
  },

  notifyAgent: (action, details) => {
    return notifications.send(
      `Agent: ${action}`,
      details,
      { force: true }
    );
  },

  enable: () => {
    defaults.NOTIFICATIONS_ENABLED = true;
    return { enabled: true };
  },

  disable: () => {
    defaults.NOTIFICATIONS_ENABLED = false;
    return { enabled: false };
  },

  isEnabled: () => {
    return defaults.NOTIFICATIONS_ENABLED;
  }
};

module.exports = notifications;
