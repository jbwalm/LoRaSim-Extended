import random
import math
import numpy as np
import time
import operator


class placementGenerator:

    def __init__(self, nr_nodes, region_counts):
        self.nr_nodes = nr_nodes
        self.region_counts = region_counts
        self.modifier = 0.2

    def full_placement(self, configurations):
        self.pre_placement(configurations)
        #self.wave_placement(configurations)
        #self.post_placement(configurations)

    def pre_placement(self, configurations):
        start = [self.nr_nodes, 0, 0, 0, 0, 0]

        differences = []
        total = 0
        for i in range(len(self.region_counts)-1):
            total += self.region_counts[i]
            differences.append(self.nr_nodes - total)

        temp = list(start)
        mods = [0, 0, 0, 0, 0]
        for i in range(10):
            configurations.append(list(temp))
            for j in range(len(differences)):
                if start[j] != 0:
                    if mods[j] == 0:
                        mods[j] = 1.0 / (10.0 - i)
                    change = differences[j] * mods[j]
                    start[j] -= change
                    start[j+1] += change
                    temp[j] = int(round(start[j]))
                    temp[j + 1] = int(round(start[j+1]))
                else:
                    break

    def wave_placement(self, configurations):
        avg = self.nr_nodes / len(self.region_counts)

        differences = []
        for j in range(0, 6):
            difference = self.region_counts[j] - avg
            differences.append(difference)

        changes = []
        for item in differences:
            change = item * self.modifier
            changes.append(change)

        start = list(self.region_counts)
        temp = list(start)
        for i in range(0, (1/self.modifier)):
            configurations.append(list(temp))
            total = 0
            for j, item in enumerate(changes):
                start[j] -= item
                temp[j] = int(round(start[j]))
                total += temp[j]
            temp[0] -= (self.nr_nodes - total)

        changes.reverse()
        for i in range(0, (1/self.modifier)):
            temp = list(configurations[-1])
            for j, item in enumerate(changes):
                temp[j] += item
            total = 0
            for j in range(len(temp)):
                temp[j] = int(round(temp[j]))
                total += temp[j]
            temp[0] += (self.nr_nodes - total)
            configurations.append(temp)

    def post_placement(self, configurations):
        temp = []
        if len(configurations) > 20:
            temp = list(configurations[1:10])
        else:
            self.pre_placement(temp)

        temp.reverse()
        for item in temp:
            item.reverse()
            configurations.append(item)


class nodePlacer:

    def __init__(self, nodes, nrnodes, distributiontype, sensi, ptx, placement):
        self.nodes = nodes
        self.nrNodes = nrnodes
        self.distributionType = distributiontype
        self.sensi = sensi
        self.Ptx = ptx
        self.sfCounts = placement
        self.distanceFinder = maxDistFinder()

        return

    @staticmethod
    def base_math(dist, bsx, bsy):
        a = random.random()
        b = random.random()
        if b < a:
            a, b = b, a
        x = b * dist * math.cos(2 * math.pi * a / b) + bsx
        y = b * dist * math.sin(2 * math.pi * a / b) + bsy
        dist = np.sqrt((x - bsx) * (x - bsx) + (y - bsy) * (y - bsy))

        return x, y, dist

    def logic(self, maxdist, bsx, bsy, nodeid):
        x = 0
        y = 0
        dist = 0

        if self.distributionType == "uniform":
            x, y, dist = self.uniform_place(maxdist, bsx, bsy)
        elif self.distributionType == "uniform basic":
            x, y, dist = self.uniform_place_basic(maxdist, bsx, bsy)
        elif self.distributionType == "controlled":
            x, y, dist = self.controlled_place(bsx, bsy, nodeid)

        return x, y, dist

    def controlled_place(self, bsx, bsy, nodeid):
        x = 0
        y = 0
        dist = -1
        region = -1
        sum = 0
        for i, sfCount in enumerate(self.sfCounts):
            sum += sfCount
            if nodeid < sum:
                region = i
                break
        if region == -1:
            region = len(self.sfCounts - 1)

        # currently assuming static txPower of 14dB
        rssi = self.Ptx + (-1 * self.sensi[region, 1])
        region_max_distance = self.distanceFinder.max_distance(rssi)
        if region > 0:
            min_rssi = self.Ptx + (-1 * self.sensi[region - 1, 1])
            region_min_distance = self.distanceFinder.max_distance(min_rssi)
        else:
            region_min_distance = 15  # 0 number 15 introduces ma deadzone which is 12.64 metres

        # Very bad way to account for minimum allowed distance.
        while dist < region_min_distance or dist > region_max_distance:
            x, y, dist = self.base_math(region_max_distance, bsx, bsy)

        return x, y, dist

    def uniform_place_basic(self, max_dist, bsx, bsy):
        x, y, dist = self.base_math(max_dist, bsx, bsy)

        return x, y, dist

    def uniform_place(self, max_dist, bsx, bsy):
        found = 0
        rounds = 0
        x = 0.0
        y = 0.0

        while found == 0 and rounds < 100:
            posx, posy, dist = self.base_math(max_dist, bsx, bsy)
            if len(self.nodes) > 0:
                for index, n in enumerate(self.nodes):
                    dist = np.sqrt(((abs(n.x - posx)) ** 2) + ((abs(n.y - posy)) ** 2))
                    if dist >= 10:
                        found = 1
                        x = posx
                        y = posy
                    else:
                        rounds = rounds + 1
                        if rounds == 100:
                            print("could not place new node, giving up")
                            exit(-1)
            else:
                x = posx
                y = posy
                found = 1
        dist = np.sqrt((x - bsx) * (x - bsx) + (y - bsy) * (y - bsy))

        return x, y, dist


class experiments:

    def __init__(self, xperiment, nr_channels, sensi, plen, gl, ptx):
        self.experiment = xperiment
        self.esti = estimator()
        self.nrChannels = nr_channels
        self.sensi = sensi
        self.plen = plen
        self.GL = gl
        self.ptx = ptx
        self.sfCounts = [0, 0, 0, 0, 0, 0]
        self.sfs = [7.0, 8.0, 9.0, 10.0, 11.0, 12.0]

    def logic(self, nodes, ideal, truth):
        if self.experiment == 1:
            self.basic_experiment(nodes, 12, 4, 125)
        elif self.experiment == 2:
            self.basic_experiment(nodes, 7, 1, 125)
        elif self.experiment == 3:
            self.basic_experiment(nodes, 12, 1, 125)
        elif self.experiment == 4:
            self.experiment_four(nodes)
        elif self.experiment == 5:
            self.experiment_five(nodes, ideal, [], truth, len(nodes))
        else:
            print("Invalid experiment!\nQuitting!")
            quit()

    def basic_experiment(self, nodes, sf, cr, bw):
        for node in nodes:
            ch = random.randint(0, self.nrChannels - 1)
            rectime = self.esti.airtime(sf, cr, self.plen, bw)
            node.packet.phase_two(sf, cr, bw, ch, rectime)
            self.sfCounts[sf - 7] += 1

    def experiment_four(self, nodes):
        for node in nodes:
            ch = random.randint(0, self.nrChannels - 1)
            minairtime = 9999
            sf = 0
            for i in range(0, 6):
                if self.sensi[i, 1] <= (self.ptx - self.GL - node.packet.Lpl):
                    sf = int(self.sensi[i, 0])
                    minairtime = self.esti.airtime(sf, 1, self.plen, 125)
                    break
            if minairtime == 9999:
                print "does not reach base station"
                exit(-1)

            rectime = self.esti.airtime(sf, 1, self.plen, 125)
            node.packet.phase_two(sf, 1, 125, ch, rectime)
            self.sfCounts[sf - 7] += 1

    # recursive method. - cancel that. just recalculate actual on the way out.
    # still working on back tracking issue.
    def experiment_five(self, nodes, ideal, actual, truth, nrNodes):
        sf_possible = [0, 0, 0, 0, 0, 0]
        temp_total = 0
        for i, amt in enumerate(truth):
            temp_total += amt
            sf_possible[i] = temp_total

        used_total = 0
        for i, total in enumerate(sf_possible):
            difference = total - used_total
            if ideal[i] <= difference:
                actual.append(ideal[i])
                used_total += ideal[i]
            else:
                actual.append(difference)
                used_total += difference
                fair_sf_getter = fairSF(nrNodes - used_total , self.sfs[i + 1:])
                ideal = ideal[:i+1] + fair_sf_getter.get_sf_counts()

                ratio = truth[i] / ideal[i]
                equivalent = ratio * ideal[i - 1]
                if i > 0 and equivalent < ideal[i-1]:
                    split_total = actual[i] + actual[i-1]
                    fair_sf_getter = fairSF(split_total, self.sfs[i-1:i+1])
                    split_ideal = fair_sf_getter.get_sf_counts()
                    actual[i-1] = split_ideal[0]
                    actual[i] = split_ideal[1]

        counter = 0
        for i, count in enumerate(actual):
            for j in range(count):
                sf = i + 7
                ch = random.randint(0, self.nrChannels - 1)
                rectime = self.esti.airtime(sf, 1, self.plen, 125)
                nodes[counter].packet.phase_two(sf, 1, 125, ch, rectime)
                self.sfCounts[sf - 7] += 1
                counter += 1


class powerControl:

    def __init__(self, power_scheme, sensi, sensi_diff, gl, ptx):
        self.powerScheme = power_scheme
        self.sensi = sensi
        self.sensiDiff = sensi_diff
        self.GL = gl
        self.ptx = ptx
        self.atrGet = operator.attrgetter

    def logic(self, nodes):
        if self.powerScheme == 1:
            self.power_one(nodes)
        elif self.powerScheme == 2:
            self.power_two(nodes)
        elif self.powerScheme == 3:
            self.power_three(nodes)
        else:
            for node in nodes:
                node.packet.phase_three(self.ptx)

    def power_one(self, nodes):
        for node in nodes:
            minsensi = self.sensi[node.packet.sf - 7, 1]
            txpow = max(2, self.ptx - math.floor((self.ptx - node.packet.Lpl) - minsensi))
            node.packet.phase_three(txpow)

    # FADR - Fair Adaptive Data Rate
    # I have implemented their power control system
    def power_two(self, nodes):
        # First sort nodes by RSSI, done with __lt__ method on node class.
        nodes_sorted = nodes
        nodes_sorted.sort()

        # get max/min RSSI and min CIR (inter SF collision?)
        min_rssi = min(nodes_sorted, key=self.atrGet('packet.rssi')).packet.rssi
        max_rssi = max(nodes_sorted, key=self.atrGet('packet.rssi')).packet.rssi
        min_cir = 8

        # Find range of power levels to use
        power_levels = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        min_power = power_levels.pop(0)
        max_power = None
        print min_rssi, max_rssi
        for i, power_level in enumerate(power_levels):
            max_power = power_level
            if (max_rssi + min_power - min_rssi - max_power) <= min_cir:
                power_levels = power_levels[0: i]
                break
            elif power_level == max(power_levels):
                max_power = power_levels.pop()

        # Recalc min_rssi, max_rssi
        min_rssi = min(min_rssi + max_power, max_rssi + min_power)
        # max_rssi = max(min_rssi + max_power, max_rssi + min_power). Need to revisit why this is calced.

        # Assign minimum power and save minPowerIndex
        min_power_index = None
        for i, n in enumerate(nodes_sorted):
            if n.packet.rssi + min_power > min_rssi:
                min_power_index = i - 1
                print ("here", i)
                break
            else:
                n.packet.phase_three(min_power)

        # Assign maximum power and save maxPowerIndex
        max_power_index = None
        for i, n in enumerate(reversed(nodes_sorted)):
            if n.packet.rssi + max_power - min_rssi > min_cir:
                max_power_index = i - 1
                break
            else:
                n.packet.phase_three(max_power)

        # Assign the reaming power levels to the inbetween nodes
        temp_index = min_power_index
        max_node_rssi = nodes_sorted[max_power_index].packet.rssi
        for power_level in power_levels:
            temp_node_rssi = nodes_sorted[temp_index].packet.rssi
            if temp_node_rssi + power_level - min_rssi <= min_cir \
                    and temp_node_rssi + power_level - max_node_rssi - max_power <= min_cir:
                for i in range(temp_index, max_power_index):
                    curr_node_rssi = nodes_sorted[i].packet.rssi
                    if curr_node_rssi + power_level - max_node_rssi - max_power > min_cir:
                        temp_index = i - 1
                        break
                    else:
                        n.packet.phase_three(power_level)
        return

    def power_three(self, nodes):
        # First sort nodes by RSSI, done with __lt__ method on node class.
        nodes_sorted = nodes
        nodes_sorted.sort()
        nodes_sorted.reverse()

        start = 0
        while True:
            first_sf8 = 0
            last_sf8 = 0
            for i, n in enumerate(nodes_sorted, start):
                # Get first sf8 node for later.
                if n.packet.sf == 7:  # and nodesSorted[-1].packet.sf == 8
                    first_sf8 = i - 1
                    break
                # Main point of this for loop is to get last sf8 node.
                if n.packet.sf == 8 and nodes_sorted[i - 1].packet.sf == 9:
                    last_sf8 = i
            start += 1

            node_a = nodes_sorted[start * -1]
            node_b = nodes_sorted[last_sf8]
            cir = self.sensiDiff[node_a.packet.sf - 7][node_a.packet.sf - 7]
            if 2 - node_a.packet.Lpl - (14 - node_b.packet.Lpl) < abs(cir):
                break
            print node_a.packet.Lpl, node_b.packet.Lpl, cir
            print ("HEREEEEE, power allocation was not viable.")
            print (2 - node_a.packet.Lpl, 14 - node_b.packet.Lpl, cir)
            quit()
            # Need to reapply spreading factors
            # Will have to do the replacement phase (or do i?)

        # Assign power levels
        for i, n in enumerate(nodes_sorted, start):
            txpow = self.ptx
            if n.packet.sf == 7:
                node_a = nodes_sorted[first_sf8]
                cir = self.sensiDiff[n.packet.sf - 7][node_a.packet.sf - 7]
                if n.packet.rssi > node_a.packet.rssi:
                    txpow = 2
                else:
                    difference = node_a.packet.rssi - n.packet.rssi
                    # cir is negative value.
                    cirdiff = difference + cir
                    txpow = max(2, txpow + cirdiff)
            else:
                node_a = nodes_sorted[start * -1]
                if n.packet.rssi > node_a.packet.rssi:
                    txpow = 2
                else:
                    difference = node_a.packet.rssi - n.packet.rssi
                    # cir is negative value.
                    cirdiff = difference + cir
                    txpow = max(2, txpow + cirdiff)
            n.packet.phase_three(txpow)
            # print "testing:", n.packet.sf, cir, txpow, Prx
        return


class channelUsage(object):
    def __init__(self):
        # self.noTraffic = 0.0
        self._traffic = 0
        self.empty = False
        self.f_flag = 0.0
        self.e_flag = 0.0
        self.accum_e = 0.0
        self.accum_f = 0.0

    @property
    def traffic(self):
        return self._traffic

    @traffic.setter
    def traffic(self, value):
        self._traffic = value

        if self.traffic == 0.0 and not self.empty:
            self.empty = True
            self.e_flag = time.time()
            if self.f_flag > 0.0:
                self.accum_f += (time.time()) - self.f_flag

        if self.traffic > 0.0 and self.empty:
            self.empty = False
            self.f_flag = time.time()
            self.accum_e += (time.time()) - self.e_flag


"""
Testing LoRaSims path loss function to find the maximum distances for each SF.
needed functions and supporting information:

Lpl = Lpld0 + 10*gamma*math.log10(distance/d0)
Can rearrange above to get:
distance = d0 * 10**((Lpl-Lpld0)/10*2.08)
Above equation can give maximum distance for a given receiver sensitivity + Tx Power.
"""


class maxDistFinder:
    """
    Initialisation method
    """

    def __init__(self):
        return

    """
    This methods finds whether a given nodes packets can reach the base-station.
    This method also returns the minimum viable spreading factor.
    """

    @staticmethod
    def max_distance(max_loss):
        distance = 40 * 10 ** ((max_loss - 127.41) / 20.8)

        return distance


class fairSF:

    def __init__(self, nr_nodes, sf_list):
        self.nrNodes = nr_nodes
        self.sfList = sf_list
        self.baseResult = self.base_function
        return

    @property
    def base_function(self):
        sum_result = 0.0

        for sf in self.sfList:
            sum_result += sf / (2 ** sf)

        return sum_result

    def get_sf_counts(self):
        sf_counts = []
        total = 0

        sf_percentages = self.get_percentages()
        before_round = []
        for sfP in sf_percentages:
            temp_count = int(round(sfP * self.nrNodes))
            before_round.append(sfP * self.nrNodes)
            sf_counts.append(temp_count)
            total += temp_count

        difference = self.nrNodes - total
        sf_counts[0] += difference
        return sf_counts

    def get_percentages(self):
        sf_percentages = []

        for sf in self.sfList:
            sf_percentages.append(self.get_percentage(sf))

        return sf_percentages

    def get_percentage(self, sf):
        sf_percentage = (sf / (2 ** sf)) / self.baseResult

        return sf_percentage


class estimator:

    # this function computes the airtime of a packet
    # according to LoraDesignGuide_STD.pdf
    def __init__(self):
        pass

    @staticmethod
    def airtime(sf, cr, pl, bw):
        h = 0  # implicit header disabled (H=0) or not (H=1)
        de = 0  # low data rate optimization enabled (=1) or not (=0)
        n_pream = 8  # number of preamble symbol (12.25  from Utz paper)

        if bw == 125 and sf in [11, 12]:
            # low data rate optimization mandated for BW125 with SF11 and SF12
            de = 1
        if sf == 6:
            # can only have implicit header with SF6
            h = 1

        t_sym = (2.0 ** sf) / bw
        t_pream = (n_pream + 4.25) * t_sym
        # print "sf", sf, " cr", cr, "pl", pl, "bw", bw
        payload_symb_nb = 8 + max(math.ceil((8.0 * pl - 4.0 * sf + 28 + 16 - 20 * h)
                                            / (4.0 * (sf - 2 * de))) * (cr + 4), 0)
        t_payload = payload_symb_nb * t_sym
        return t_pream + t_payload

    @staticmethod
    def chirp_time(sf, bw):
        chirpy_time = (2 ** sf) / bw
        return chirpy_time

    # Okumura-Hata path loss model.
    @staticmethod
    def hata_urban(sensi):
        path_loss = 17.5 - sensi
        d = 10 ** ((path_loss - 124.76) / 35.22)
        print(d)