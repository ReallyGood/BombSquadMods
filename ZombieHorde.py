import bs
import random
import bsUtils
import bsSpaz
import copy
#import PlayerSpaz

def bsGetAPIVersion():
    # see bombsquadgame.com/apichanges
    return 4

def bsGetGames():
    return [ZombieHorde]


class Icon(bs.Actor):
        
    def __init__(self,player,position,scale,showLives=True,showDeath=True,
                 nameScale=1.0,nameMaxWidth=115.0,flatness=1.0,shadow=1.0):
        bs.Actor.__init__(self)

        self._player = player
        self._showLives = showLives
        self._showDeath = showDeath
        self._nameScale = nameScale

        self._outlineTex = bs.getTexture('characterIconMask')
        
        icon = player.getIcon()
        self.node = bs.newNode('image',
                               owner=self,
                               attrs={'texture':icon['texture'],
                                      'tintTexture':icon['tintTexture'],
                                      'tintColor':icon['tintColor'],
                                      'vrDepth':400,
                                      'tint2Color':icon['tint2Color'],
                                      'maskTexture':self._outlineTex,
                                      'opacity':1.0,
                                      'absoluteScale':True,
                                      'attach':'bottomCenter'})
        self._nameText = bs.newNode('text',
                                    owner=self.node,
                                    attrs={'text':player.getName(),
                                           'color':bs.getSafeColor(player.getTeam().color),
                                           'hAlign':'center',
                                           'vAlign':'center',
                                           'vrDepth':410,
                                           'maxWidth':nameMaxWidth,
                                           'shadow':shadow,
                                           'flatness':flatness,
                                           'hAttach':'center',
                                           'vAttach':'bottom'})
        if self._showLives:
            self._livesText = bs.newNode('text',
                                         owner=self.node,
                                         attrs={'text':'x0',
                                                'color':(1,1,0.5),
                                                'hAlign':'left',
                                                'vrDepth':430,
                                                'shadow':1.0,
                                                'flatness':1.0,
                                                'hAttach':'center',
                                                'vAttach':'bottom'})
        self.setPositionAndScale(position,scale)

    def setPositionAndScale(self,position,scale):
        self.node.position = position
        self.node.scale = [70.0*scale]
        self._nameText.position = (position[0],position[1]+scale*52.0)
        self._nameText.scale = 1.0*scale*self._nameScale
        if self._showLives:
            self._livesText.position = (position[0]+scale*10.0,position[1]-scale*43.0)
            self._livesText.scale = 1.0*scale

    def updateForLives(self):
        if self._player.exists():
            lives = self._player.gameData['lives']
        else: lives = 0
        if self._showLives:
            if lives > 0: self._livesText.text = 'x'+str(lives-1)
            else: self._livesText.text = ''
        if lives == 0:
            self._nameText.opacity = 0.2
            self.node.color = (0.7,0.3,0.3)
            self.node.opacity = 0.2
        
    def handlePlayerSpawned(self):
        if not self.node.exists(): return
        self.node.opacity = 1.0
        self.updateForLives()

    def handlePlayerDied(self):
        if not self.node.exists(): return
        if self._showDeath:
            bs.animate(self.node,'opacity',{0:1.0,50:0.0,100:1.0,150:0.0,200:1.0,250:0.0,
                                            300:1.0,350:0.0,400:1.0,450:0.0,500:1.0,550:0.2})
            lives = self._player.gameData['lives']
            if lives == 0: bs.gameTimer(600,self.updateForLives)
        
class PlayerSpaz_Zom(bs.PlayerSpaz):
    def handleMessage(self, m):
        if isinstance(m, bs.HitMessage):
            if not self.node.exists():
                return
            if not m.sourcePlayer is None:
                #it seems as though spazBots are actually players, but with invalid names... Do a try for invalid name?
                try:
                    playa = m.sourcePlayer.getName(True, False) # Long name, no icons
                    if not playa is None:
                        #Player had a name.  Hit by a person. No damage.
                        pass
                except:
                    super(self.__class__, self).handleMessage(m)
            else:
                super(self.__class__, self).handleMessage(m)
        elif isinstance(m,bs.FreezeMessage):
            pass #Can't be frozen.  Would allow self-freeze, but can't prevent others from freezing.
        else:
            super(self.__class__, self).handleMessage(m)
            
class ZombieHorde(bs.TeamGameActivity):

    @classmethod
    def getName(cls):
        return 'Zombie Horde'

    @classmethod
    def getScoreInfo(cls):
        return {'scoreName':'score',
                'scoreType':'points',
                'noneIsWinner':False,
                'lowerIsBetter':False}
    
    @classmethod
    def getDescription(cls,sessionType):
        return 'Kill walkers, not players!'

    @classmethod
    def supportsSessionType(cls,sessionType):
        return True if (issubclass(sessionType,bs.TeamsSession)
                        or issubclass(sessionType,bs.FreeForAllSession)) else False

    @classmethod
    def getSupportedMaps(cls,sessionType):
        return bs.getMapsSupportingPlayType("melee")

    @classmethod
    def getSettings(cls,sessionType):
        settings = [("Lives Per Player",{'default':1,'minValue':1,'maxValue':10,'increment':1}),
                    ("Max Zombies", {'default':10,'minValue':5, 'maxValue':50,'increment':5}),
                    ("Time Limit",{'choices':[('None',0),('1 Minute',60),
                                            ('2 Minutes',120),('5 Minutes',300),
                                            ('10 Minutes',600),('20 Minutes',1200)],'default':120}),
                    ("Respawn Times",{'choices':[('Shorter',0.25),('Short',0.5),('Normal',1.0),('Long',2.0),('Longer',4.0)],'default':1.0}),
                    ("Epic Mode",{'default':False})]

        if issubclass(sessionType,bs.TeamsSession):
            settings.append(("Solo Mode",{'default':False}))
            settings.append(("Balance Total Lives",{'default':False}))
            
        return settings

    def __init__(self,settings):
        bs.TeamGameActivity.__init__(self,settings)
        if self.settings['Epic Mode']: self._isSlowMotion = True
        
        # show messages when players die since it's meaningful here
        self.announcePlayerDeaths = True
        
        try: self._soloMode = settings['Solo Mode']
        except Exception: self._soloMode = False
        self._scoreBoard = bs.ScoreBoard()
        self.spazList = []
        self.zombieQ = 0

    def getInstanceDescription(self):
        return 'Kill walkers, not players!' if isinstance(self.getSession(),bs.TeamsSession) else 'Kill walkers, not players!'

    def getInstanceScoreBoardDescription(self):
        return 'Kill walkers, not players!' if isinstance(self.getSession(),bs.TeamsSession) else 'Kill walkers, not players!'

    def onTransitionIn(self):
        bs.TeamGameActivity.onTransitionIn(self, music='Epic' if self.settings['Epic Mode'] else 'Survival')
        self._startGameTime = bs.getGameTime()

    def onTeamJoin(self,team):
        team.gameData['score'] = 0
        team.gameData['spawnOrder'] = []
        self._updateScoreBoard()

    def onPlayerJoin(self, player):

        # no longer allowing mid-game joiners here... too easy to exploit
        if self.hasBegun():
            player.gameData['lives'] = 0
            player.gameData['icons'] = []
            # make sure our team has survival seconds set if they're all dead
            # (otherwise blocked new ffa players would be considered 'still alive' in score tallying)
            #if self._getTotalTeamLives(player.getTeam()) == 0 and player.getTeam().gameData['survivalSeconds'] is None:
            #    player.getTeam().gameData['survivalSeconds'] = 1000
            bs.screenMessage(bs.Lstr(resource='playerDelayedJoinText',subs=[('${PLAYER}',player.getName(full=True))]),color=(0,1,0))
            return
        
        player.gameData['lives'] = self.settings['Lives Per Player']

        if self._soloMode:
            player.gameData['icons'] = []
            player.getTeam().gameData['spawnOrder'].append(player)
            self._updateSoloMode()
        else:
            # create our icon and spawn
            player.gameData['icons'] = [Icon(player,position=(0,50),scale=0.8)]
            if player.gameData['lives'] > 0:
                self.spawnPlayer(player)

        # dont waste time doing this until begin
        if self.hasBegun():
            self._updateIcons()

    def _updateSoloMode(self):
        # for both teams, find the first player on the spawn order list with lives remaining
        # and spawn them if they're not alive
        for team in self.teams:
            # prune dead players from the spawn order
            team.gameData['spawnOrder'] = [p for p in team.gameData['spawnOrder'] if p.exists()]
            for player in team.gameData['spawnOrder']:
                if player.gameData['lives'] > 0:
                    if not player.isAlive(): self.spawnPlayer(player)
                    break

    def _updateIcons(self):
        # in free-for-all mode, everyone is just lined up along the bottom
        if isinstance(self.getSession(),bs.FreeForAllSession):
            count = len(self.teams)
            xOffs = 85
            x = xOffs*(count-1) * -0.5
            for i,team in enumerate(self.teams):
                if len(team.players) == 1:
                    player = team.players[0]
                    for icon in player.gameData['icons']:
                        icon.setPositionAndScale((x,30),0.7)
                        icon.updateForLives()
                    x += xOffs

        # in teams mode we split up teams
        else:
            if self._soloMode:
                # first off, clear out all icons
                for player in self.players:
                    player.gameData['icons'] = []
                # now for each team, cycle through our available players adding icons
                for team in self.teams:
                    if team.getID() == 0:
                        x = -60
                        xOffs = -78
                    else:
                        x = 60
                        xOffs = 78
                    isFirst = True
                    testLives = 1
                    while True:
                        playersWithLives = [p for p in team.gameData['spawnOrder'] if p.exists() and p.gameData['lives'] >= testLives]
                        if len(playersWithLives) == 0: break
                        for player in playersWithLives:
                            player.gameData['icons'].append(Icon(player,
                                                                 position=(x,(40 if isFirst else 25)),
                                                                 scale=1.0 if isFirst else 0.5,
                                                                 nameMaxWidth=130 if isFirst else 75,
                                                                 nameScale=0.8 if isFirst else 1.0,
                                                                 flatness=0.0 if isFirst else 1.0,
                                                                 shadow=0.5 if isFirst else 1.0,
                                                                 showDeath=True if isFirst else False,
                                                                 showLives=False))
                            x += xOffs * (0.8 if isFirst else 0.56)
                            isFirst = False
                        testLives += 1
            # non-solo mode
            else:
                for team in self.teams:
                    if team.getID() == 0:
                        x = -50
                        xOffs = -85
                    else:
                        x = 50
                        xOffs = 85
                    for player in team.players:
                        for icon in player.gameData['icons']:
                            icon.setPositionAndScale((x,30),0.7)
                            icon.updateForLives()
                        x += xOffs
                    
    def _getSpawnPoint(self,player):
        # in solo-mode, if there's an existing live player on the map, spawn at whichever
        # spot is farthest from them (keeps the action spread out)
        if self._soloMode:
            livingPlayer = None
            for team in self.teams:
                for player in team.players:
                    if player.isAlive():
                        p = player.actor.node.position
                        livingPlayer = player
                        livingPlayerPos = p
                        break
            if livingPlayer:
                playerPos = bs.Vector(*livingPlayerPos)
                points = []
                for team in self.teams:
                    startPos = bs.Vector(*self.getMap().getStartPosition(team.getID()))
                    points.append([(startPos-playerPos).length(),startPos])
                points.sort()
                return points[-1][1]
            else:
                return None
        else:
            return None

        
    def spawnPlayer(self,player):
        """This next line is the default spawn line. But we need to spawn our special guy"""
        #self.spawnPlayerSpaz(player,self._getSpawnPoint(player))
        #position = self._getSpawnPoint(player)
        #if isinstance(self.getSession(), bs.TeamsSession):
        #    position = self.getMap().getStartPosition(player.getTeam().getID())
        #else:
        #	# otherwise do free-for-all spawn locations
        position = self.getMap().getFFAStartPosition(self.players)

        angle = 20


        #spaz = self.spawnPlayerSpaz(player)

        # lets reconnect this player's controls to this
        # spaz but *without* the ability to attack or pick stuff up
        #spaz.connectControlsToPlayer(enablePunch=False,
        #							 enableBomb=False,
        #							 enablePickUp=False)

        # also lets have them make some noise when they die..
        #spaz.playBigDeathSound = True

        name = player.getName()

        lightColor = bsUtils.getNormalizedColor(player.color)
        displayColor = bs.getSafeColor(player.color, targetIntensity=0.75)

        spaz = PlayerSpaz_Zom(color=player.color,
                             highlight=player.highlight,
                             character=player.character,
                             player=player)
        player.setActor(spaz)
        #For some reason, I can't figure out how to get a list of all spaz.
        #Therefore, I am making the list here so I can get which spaz belongs
        #to the player supplied by HitMessage.
        self.spazList.append(spaz)
        # we want a bigger area-of-interest in co-op mode
        # if isinstance(self.getSession(),bs.CoopSession): spaz.node.areaOfInterestRadius = 5.0
        # else: spaz.node.areaOfInterestRadius = 5.0

        # if this is co-op and we're on Courtyard or Runaround, add the material that allows us to
        # collide with the player-walls
        # FIXME; need to generalize this
        if isinstance(self.getSession(), bs.CoopSession) and self.getMap().getName() in ['Courtyard', 'Tower D']:
            mat = self.getMap().preloadData['collideWithWallMaterial']
            spaz.node.materials += (mat,)
            spaz.node.rollerMaterials += (mat,)

        spaz.node.name = name
        spaz.node.nameColor = displayColor
        spaz.connectControlsToPlayer(enablePickUp=False) #Unfortunately, I can't figure out how to prevent picking up other player but allow other pickup.
        self.scoreSet.playerGotNewSpaz(player, spaz)

        # move to the stand position and add a flash of light
        spaz.handleMessage(bs.StandMessage(position, angle if angle is not None else random.uniform(0, 360)))
        t = bs.getGameTime()
        bs.playSound(self._spawnSound, 1, position=spaz.node.position)
        light = bs.newNode('light', attrs={'color': lightColor})
        spaz.node.connectAttr('position', light, 'position')
        bsUtils.animate(light, 'intensity', {0: 0, 250: 1, 500: 0})
        bs.gameTimer(500, light.delete)
        #Start code to spawn special guy:
        #End of code to spawn special guy
        if not self._soloMode:
            bs.gameTimer(300,bs.Call(self._printLives,player))

        # if we have any icons, update their state
        for icon in player.gameData['icons']:
            icon.handlePlayerSpawned()

    def _printLives(self,player):
        if not player.exists() or not player.isAlive(): return
        try: pos = player.actor.node.position
        except Exception,e:
            print 'EXC getting player pos in bsElim',e
            return
        bs.PopupText('x'+str(player.gameData['lives']-1),color=(1,1,0,1),
                           offset=(0,-0.8,0),randomOffset=0.0,scale=1.8,position=pos).autoRetain()

    def onPlayerLeave(self,player):

        bs.TeamGameActivity.onPlayerLeave(self,player)

        player.gameData['icons'] = None

        # remove us from spawn-order
        if self._soloMode:
            if player in player.getTeam().gameData['spawnOrder']:
                player.getTeam().gameData['spawnOrder'].remove(player)

        # update icons in a moment since our team will be gone from the list then
        bs.gameTimer(0, self._updateIcons)


    def onBegin(self):
        bs.TeamGameActivity.onBegin(self)
        self.setupStandardTimeLimit(self.settings['Time Limit'])
        self.setupStandardPowerupDrops()
        self.zombieQ = 1 # queue of zombies to spawn. this will increment/decrement 
        if self._soloMode:
            self._vsText = bs.NodeActor(bs.newNode("text",
                                                   attrs={'position':(0,105),
                                                          'hAttach':"center",
                                                          'hAlign':'center',
                                                          'maxWidth':200,
                                                          'shadow':0.5,
                                                          'vrDepth':390,
                                                          'scale':0.6,
                                                          'vAttach':"bottom",
                                                          'color':(0.8,0.8,0.3,1.0),
                                                          'text':bs.Lstr(resource='vsText')}))

        # if balance-team-lives is on, add lives to the smaller team until total lives match
        if (isinstance(self.getSession(),bs.TeamsSession)
            and self.settings['Balance Total Lives']
            and len(self.teams[0].players) > 0
            and len(self.teams[1].players) > 0):
            if self._getTotalTeamLives(self.teams[0]) < self._getTotalTeamLives(self.teams[1]):
                lesserTeam = self.teams[0]
                greaterTeam = self.teams[1]
            else:
                lesserTeam = self.teams[1]
                greaterTeam = self.teams[0]
            addIndex = 0
            while self._getTotalTeamLives(lesserTeam) < self._getTotalTeamLives(greaterTeam):
                lesserTeam.players[addIndex].gameData['lives'] += 1
                addIndex = (addIndex + 1) % len(lesserTeam.players)
        #Let's add a couple of bots
        # this wrangles our bots
        self._bots = bs.BotSet()
        
        #Load up appearances. We want to make Walkers look crazy!
        #Since no bots exist yet, we have to load up the factory manually.
        activity = bs.getActivity()
        try: myFactory = activity._sharedSpazFactory
        except Exception:
            myFactory = activity._sharedSpazFactory = bsSpaz.SpazFactory()
        #Load up resources for our composite model
        appears=['Kronk','Zoe','Pixel','Agent Johnson','Bones','Frosty','Kronk2']
        myAppear = copy.copy(bsSpaz.appearances['Kronk'])
        myAppear.name = 'Kronk2'
        bsSpaz.appearances['Kronk2'] = myAppear
        for appear in appears:
            myFactory._getMedia(appear)
        #Now all the media is loaded up for the spazzes we are pulling from. 
        #Now edit Kronk2 and set ToughGuyBot character to Kronk2
        # Because these are zombies, let's make 'em green. Change the ToughGuyBot colors to green. Reset during end game.

        med = myFactory.spazMedia
        head = random.choice(med.keys())
        med['Kronk2']['headModel'] = med['Zoe']['headModel']
        med['Kronk2']['colorTexture']=med['Agent Johnson']['colorTexture']
        med['Kronk2']['colorMaskTexture']=med['Pixel']['colorMaskTexture']
        med['Kronk2']['torsoModel'] = med['Bones']['torsoModel']
        med['Kronk2']['pelvisModel'] = med['Pixel']['pelvisModel']
        med['Kronk2']['upperArmModel'] = med['Frosty']['upperArmModel']
        med['Kronk2']['foreArmModel'] = med['Frosty']['foreArmModel']
        med['Kronk2']['handModel'] = med['Bones']['handModel']
        med['Kronk2']['upperLegModel'] = med['Bones']['upperLegModel']
        med['Kronk2']['lowerLegModel'] = med['Pixel']['lowerLegModel']
        med['Kronk2']['toesModel'] = med['Bones']['toesModel']
        setattr(bs.ToughGuyBot, 'color', (0.4,0.1,0.05))
        setattr(bs.ToughGuyBot, 'highlight', (0.2,0.4,0.3))
        setattr(bs.ToughGuyBot, 'character', 'Kronk2')
        # start some timers to spawn bots
        thePt = self.getMap().getFFAStartPosition(self.players)
        #bs.gameTimer(1000,bs.Call(self._bots.spawnBot,bs.ToughGuyBot,pos=thePt,spawnTime=3000))
        
        self._updateIcons()
        self._updateScoreBoard

        # we could check game-over conditions at explicit trigger points,
        # but lets just do the simple thing and poll it...
        bs.gameTimer(1000, self._update, repeat=True)
        
    def _getTotalTeamLives(self,team):
        return sum(player.gameData['lives'] for player in team.players)

    def handleMessage(self,m):
        if isinstance(m,bs.PlayerSpazDeathMessage):
            
            bs.TeamGameActivity.handleMessage(self, m) # augment standard behavior
            player = m.spaz.getPlayer()
            #print([player, m.spaz.hitPoints, "killed by", m.killerPlayer])
            
            player.gameData['lives'] -= 1
                
            #Remove this spaz from the list of active spazzes
            if m.spaz in self.spazList: self.spazList.remove(m.spaz)
            if player.gameData['lives'] < 0:
                bs.printError('Got lives < 0 in Elim; this shouldnt happen. solo:'+str(self._soloMode))
                player.gameData['lives'] = 0

            # if we have any icons, update their state
            for icon in player.gameData['icons']:
                icon.handlePlayerDied()

            # play big death sound on our last death or for every one in solo mode
            if self._soloMode or player.gameData['lives'] == 0:
                bs.playSound(bs.Spaz.getFactory().singlePlayerDeathSound)

            # if we hit zero lives, we're dead (and our team might be too)
            if player.gameData['lives'] == 0:
                # if the whole team is now dead, mark their survival time..
                #if all(teammate.gameData['lives'] == 0 for teammate in player.getTeam().players):
                #ZombieHorde: don't care survival time
                #if self._getTotalTeamLives(player.getTeam()) == 0:
                #    player.getTeam().gameData['survivalSeconds'] = (bs.getGameTime()-self._startGameTime)/1000
                pass
            else:
                # otherwise, in regular mode, respawn..
                if not self._soloMode:
                    self.respawnPlayer(player)

            # in solo, put ourself at the back of the spawn order
            if self._soloMode:
                player.getTeam().gameData['spawnOrder'].remove(player)
                player.getTeam().gameData['spawnOrder'].append(player)
        elif isinstance(m,bs.SpazBotDeathMessage):
            self._onSpazBotDied(m)
            bs.TeamGameActivity.handleMessage(self,m)
            #bs.PopupText("died",position=self._position,color=popupColor,scale=popupScale).autoRetain()
        else:
            bs.TeamGameActivity.handleMessage(self,m)
    def _update(self):
        #self.randZombie()
        #Check if we neeed more zombies
        if self.zombieQ > 0:
            self.zombieQ -= 1
            self.spawnZombie()
        if self._soloMode:
            # for both teams, find the first player on the spawn order list with lives remaining
            # and spawn them if they're not alive
            for team in self.teams:
                # prune dead players from the spawn order
                team.gameData['spawnOrder'] = [p for p in team.gameData['spawnOrder'] if p.exists()]
                for player in team.gameData['spawnOrder']:
                    if player.gameData['lives'] > 0:
                        if not player.isAlive():
                            self.spawnPlayer(player)
                            self._updateIcons()
                        break
        
        # if we're down to 1 or fewer living teams, start a timer to end the game
        # (allows the dust to settle and draws to occur if deaths are close enough)
        #Actually, since this is Zombie Horde, let's allow the last player to die in case they are behind. So less than 1 living team.
        teamsRemain = self._getLivingTeams()
        if len(teamsRemain) < 2:
            if len(teamsRemain) == 1:
                theScores = []
                for team in self.teams:
                    theScores.append(team.gameData['score'])
                if teamsRemain[0].gameData['score']< max(theScores):
                    pass # the last guy doesn't have the best score
                elif teamsRemain[0].gameData['score'] == max(theScores) and theScores.count(max(theScores)) > 1:
                    pass #The last guy left is tied for the lead!  Can he get one more?
                else:
                    self._roundEndTimer = bs.Timer(500,self.endGame)
            else:
                self._roundEndTimer = bs.Timer(500,self.endGame)
                

    def spawnZombie(self):
        #We need a Z height...
        thePt = [0,0,0]
        thePt2 = self.getMap().getFFAStartPosition(self.players)
        x = random.uniform(-1.0,1.0)
        y = random.uniform(-1.0,1.0)
        thePt[0] = 5.0*x
        thePt[1] = thePt2[1]
        thePt[2] = 5.0*y
        bs.gameTimer(100,bs.Call(self._bots.spawnBot,bs.ToughGuyBot,pos=thePt,spawnTime=1000))
            
    def _onSpazBotDied(self,DeathMsg):
        #Just in case we are over max...
        if len(self._bots.getLivingBots()) < self.settings['Max Zombies']:
            #Go ahead and replace dead zombie, no matter how it died
            self.zombieQ +=1

            if DeathMsg.killerPlayer is None:
                pass
            else:
                player = DeathMsg.killerPlayer
                #print(player)
                if not player.exists(): return # could happen if they leave after throwing a bomb..
                player.getTeam().gameData['score'] += 1
                #player.getTeam().gameData['kills'] += 1
                #if kill was legit, spawn a zombie!
                self.zombieQ += 1
                self._updateScoreBoard()
            
    def _updateScoreBoard(self):
        for team in self.teams:
            self._scoreBoard.setTeamValue(team, team.gameData['score'])
    def _getLivingTeams(self):
        return [team for team in self.teams if len(team.players) > 0 and any(player.gameData['lives'] > 0 for player in team.players)]

    def endGame(self):
        if self.hasEnded(): return
        #Reset the default color for the ToughGuyBot
        setattr(bs.ToughGuyBot, 'color', (0.6,0.6,0.6))
        setattr(bs.ToughGuyBot, 'highlight', (0.6,0.6,0.6))
        setattr(bs.ToughGuyBot, 'character', 'Kronk')
        results = bs.TeamGameResults()
        self._vsText = None # kill our 'vs' if its there
        for team in self.teams:
            results.setTeamScore(team, team.gameData['score'])
        self.end(results=results)
        
