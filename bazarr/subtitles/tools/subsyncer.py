# coding=utf-8

import logging
import os

from ffsubsync.ffsubsync import run, make_parser

from utilities.binaries import get_binary
from radarr.history import history_log_movie
from sonarr.history import history_log
from subtitles.processing import ProcessSubtitlesResult
from languages.get_languages import language_from_alpha2
from utilities.path_mappings import path_mappings
from app.config import settings
from app.get_args import args


class SubSyncer:
    def __init__(self):
        self.reference = None
        self.srtin = None
        self.srtout = None
        self.ffmpeg_path = None
        self.args = None
        try:
            import webrtcvad  # noqa W0611
        except ImportError:
            self.vad = 'subs_then_auditok'
        else:
            self.vad = 'subs_then_webrtc'
        self.log_dir_path = os.path.join(args.config_dir, 'log')

    def sync(self, video_path, srt_path, srt_lang, media_type, sonarr_series_id=None, sonarr_episode_id=None,
             radarr_id=None):
        self.reference = video_path
        self.srtin = srt_path
        self.srtout = '{}.synced.srt'.format(os.path.splitext(self.srtin)[0])
        self.args = None

        ffprobe_exe = get_binary('ffprobe')
        if not ffprobe_exe:
            logging.debug('BAZARR FFprobe not found!')
            return
        else:
            logging.debug('BAZARR FFprobe used is %s', ffprobe_exe)

        ffmpeg_exe = get_binary('ffmpeg')
        if not ffmpeg_exe:
            logging.debug('BAZARR FFmpeg not found!')
            return
        else:
            logging.debug('BAZARR FFmpeg used is %s', ffmpeg_exe)

        self.ffmpeg_path = os.path.dirname(ffmpeg_exe)
        unparsed_args = [self.reference, '-i', self.srtin, '-o', self.srtout, '--ffmpegpath', self.ffmpeg_path, '--vad',
                         self.vad, '--log-dir-path', self.log_dir_path]
        if settings.subsync.getboolean('force_audio'):
            unparsed_args.append('--no-fix-framerate')
            unparsed_args.append('--reference-stream')
            unparsed_args.append('a:0')
        if settings.subsync.getboolean('debug'):
            unparsed_args.append('--make-test-case')
        parser = make_parser()
        self.args = parser.parse_args(args=unparsed_args)
        if os.path.isfile(self.srtout):
            os.remove(self.srtout)
            logging.debug('BAZARR deleted the previous subtitles synchronization attempt file.')
        try:
            result = run(self.args)
        except Exception:
            logging.exception('BAZARR an exception occurs during the synchronization process for this subtitles: '
                              '{0}'.format(self.srtin))
            raise OSError
        else:
            if settings.subsync.getboolean('debug'):
                return result
            if os.path.isfile(self.srtout):
                if not settings.subsync.getboolean('debug'):
                    os.remove(self.srtin)
                    os.rename(self.srtout, self.srtin)

                    offset_seconds = result['offset_seconds'] or 0
                    framerate_scale_factor = result['framerate_scale_factor'] or 0
                    message = "{0} subtitles synchronization ended with an offset of {1} seconds and a framerate " \
                              "scale factor of {2}.".format(language_from_alpha2(srt_lang), offset_seconds,
                                                            "{:.2f}".format(framerate_scale_factor))

                    result = ProcessSubtitlesResult(message=message,
                                                    reversed_path=path_mappings.path_replace_reverse(self.reference),
                                                    downloaded_language_code2=srt_lang,
                                                    downloaded_provider=None,
                                                    score=None,
                                                    forced=None,
                                                    subtitle_id=None,
                                                    reversed_subtitles_path=srt_path,
                                                    hearing_impaired=None)

                    if media_type == 'series':
                        history_log(action=5, sonarr_series_id=sonarr_series_id, sonarr_episode_id=sonarr_episode_id,
                                    result=result)
                    else:
                        history_log_movie(action=5, radarr_id=radarr_id, result=result)
            else:
                logging.error('BAZARR unable to sync subtitles: {0}'.format(self.srtin))

            return result
